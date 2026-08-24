// blurlab candidate 10. Candidate 4 is still the champion after five failed
// challengers (5-9 all landed between 5.96x and 6.68x), so the lesson from this
// generation is that the cand4 graph shape is load-bearing and fragile: every
// challenger that restructured the pipeline paid for it. This candidate
// therefore keeps the cand4 graph *exactly* as it is -- same blur domain, same
// sigmas, same feather, same crop/clamp ordering, same final blend -- and only
// removes work that provably does not change a single output pixel, plus the
// one lever whose SSIM cost we have now measured directly.
//
// What the ledger says about mask lag. Candidate 3 ran interval 2 (mean lag
// 0.5) and scored 0.99940. Candidate 4 ran interval 4 (mean lag 1.5, worst lag
// 3) and scored 0.99927. Tripling the mean lag cost 0.00013 SSIM. That is the
// real, measured price of temporal mask reuse on this clip, and it is roughly
// 0.0001 per frame of additional mean lag -- two orders of magnitude below the
// 0.02 of headroom the mean gate leaves us, and the worst frame is nowhere near
// the 0.95 floor. Meanwhile Vision is still the only per-frame block big enough
// to see, and its cost is exactly proportional to 1/interval.
//
// So: interval 4 -> 8. Mean lag goes 1.5 -> 3.5, worst lag 3 -> 7. Even if the
// lag/SSIM relation is quadratic rather than the linear one the two data points
// support, the mean lands near 0.996 and the worst frame near 0.985 -- still
// clear of both gates by a wide margin. In exchange the amortised Vision term
// halves, which is the single largest identifiable saving left.
//
// Two exact, output-identical savings ride along:
//
//   * The CIColorInvert on the mask is gone. bgCut wanted "the frame, with the
//     subject punched out". Candidate 4 built that as
//     blend(input: frame, background: transparent, mask: 1 - subjectMask),
//     which needs an inversion pass over the half-res mask every frame.
//     CIBlendWithMask is symmetric under swapping its two image operands and
//     complementing the mask, so
//     blend(input: transparent, background: frame, mask: subjectMask)
//     is the same image by algebra, with one fewer filter node in the hot path.
//     It also gives the node a finite extent from the background operand
//     instead of inheriting the transparent operand's, so the crop-then-clamp
//     that keeps the border band correct is now guaranteed rather than argued.
//
//   * The derived mask views (full-res mask, blur-domain mask) are cached as
//     objects, not just recomputed from a cached recipe. On the seven reuse
//     frames out of every eight, the mask path now hands CIContext the
//     identical CIImage nodes it saw last frame, which is the precondition for
//     its intermediate cache to hit instead of re-deriving the feathered,
//     rescaled mask. Worst case this is a no-op; best case it deletes the mask
//     path entirely on 7/8 of frames. Either way the pixels are bit-identical,
//     so it carries no SSIM risk at all. The cache is keyed on the frame extent
//     and invalidated whenever a new segmentation lands.
//
// Nothing else moves: blur scale stays 0.5 (the one factor where a bilinear
// downscale is an exact 2x2 box average), sigma stays 14, the feather stays at
// 3 full-res pixels applied at Vision resolution, and the halo-free
// cut-out-blur-over-fill construction is untouched.

import CoreImage
import CoreImage.CIFilterBuiltins
import Vision
import Foundation

// EVOLVE-BLOCK-START
final class EvolvedBlurKernel {

    private let segmentationRequest: VNGeneratePersonSegmentationRequest = {
        let request = VNGeneratePersonSegmentationRequest()
        request.qualityLevel = .balanced
        request.outputPixelFormat = kCVPixelFormatType_OneComponent8
        return request
    }()

    // Temporal reuse. 8 means "segment, then reuse seven times". The measured
    // cost of mask lag on this clip is ~0.0001 SSIM per frame of mean lag
    // (candidate 3 vs candidate 4), so mean lag 3.5 stays two orders of
    // magnitude inside the 0.98 mean gate while halving the Vision term again.
    private let segmentInterval: Int = 8

    // Blur domain. 0.5 keeps the scaled sigma at 7, deep in the range where a
    // downscaled Gaussian is indistinguishable from the full-res one, and it is
    // also the one scale factor at which a bilinear downscale is exactly a 2x2
    // box average rather than a lossy point sample.
    private let blurScale: CGFloat = 0.5
    private let sigma: Double = 14
    private let featherSigmaFullRes: Double = 3

    // Cached mask state, valid because frames arrive in order and the instance
    // lives for the whole clip. The cached images are only ever consumed on
    // frames where no Vision request runs, so the underlying Vision pixel
    // buffer cannot be rewritten underneath them. Both the clamp and the two
    // derived sampler views are baked in here so that reuse frames present
    // CIContext with the identical nodes as the frame before.
    private var cachedClampedLow: CIImage?
    private var cachedFullMask: CIImage?
    private var cachedSmallMask: CIImage?
    private var cachedExtent: CGRect = .null
    private var cachedRawExtent: CGRect = .zero

    // Person-segmented background blur for the webcam. Returns the original
    // frame if the Vision request fails. frameIndex counts up from 0
    // and frames arrive in order, so state kept between calls (for example a
    // cached mask) is valid.
    func process(_ pixelBuffer: CVPixelBuffer, frameIndex: Int, ciContext: CIContext) -> CIImage {
        let original = CIImage(cvPixelBuffer: pixelBuffer)
        let extent = original.extent
        let s = blurScale

        let smallExtent = CGRect(x: extent.origin.x * s,
                                 y: extent.origin.y * s,
                                 width: extent.width * s,
                                 height: extent.height * s)

        // Run Vision only on the sampled frames, or whenever there is nothing
        // usable to reuse.
        let mustSegment = (frameIndex % segmentInterval == 0) || cachedClampedLow == nil
        var rebuildDerived = mustSegment
            || cachedFullMask == nil
            || cachedSmallMask == nil
            || extent != cachedExtent

        if mustSegment {
            let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, options: [:])
            guard (try? handler.perform([segmentationRequest])) != nil,
                  let maskBuffer = segmentationRequest.results?.first?.pixelBuffer else {
                return original
            }

            let rawMask = CIImage(cvPixelBuffer: maskBuffer)
            let rawExtent = rawMask.extent
            let sxRaw = extent.width / max(rawExtent.width, 1)

            // Feather the segmentation mask while it is still small. A sigma of
            // 3 full-resolution pixels is 3/sx mask pixels, and this pass
            // touches ~1/(sx*sy) of the pixels a post-upscale feather would.
            // Clamped once, here, at Vision resolution, so that every consumer
            // downstream is a pure sampler view and nothing in the mask path is
            // ever materialised at 1080p.
            let featherSigma = featherSigmaFullRes / Double(max(sxRaw, 1))
            cachedClampedLow = rawMask.clampedToExtent()
                .applyingGaussianBlur(sigma: featherSigma)
                .cropped(to: rawExtent)
                .clampedToExtent()
            cachedRawExtent = rawExtent
            rebuildDerived = true
        }

        guard let clampedLow = cachedClampedLow else { return original }

        if rebuildDerived {
            // Vision-to-frame scale, from the raw mask geometry recorded when
            // this mask was produced. clampedLow is infinite, so the raw extent
            // has to be carried alongside it rather than read back off the node.
            let rawExtent = cachedRawExtent
            let sx = extent.width / max(rawExtent.width, 1)
            let sy = extent.height / max(rawExtent.height, 1)

            // Full-resolution mask for the final composite: white = subject.
            // Pure transform + crop of the already-clamped low-res node, so it
            // stays a sampler the blend can read through instead of a
            // materialised pass.
            cachedFullMask = clampedLow
                .transformed(by: CGAffineTransform(scaleX: sx, y: sy))
                .cropped(to: extent)

            // The same clamped low-res mask taken straight into the blur
            // domain, so it is never materialised at full resolution on the way.
            cachedSmallMask = clampedLow
                .transformed(by: CGAffineTransform(scaleX: sx * s, y: sy * s))
                .cropped(to: smallExtent)

            cachedExtent = extent
        }

        guard let mask = cachedFullMask, let smallMask = cachedSmallMask else {
            return original
        }

        // Half-scale copy of the frame, via a plain affine instead of Lanczos.
        // At exactly 0.5 the bilinear taps land on a texel corner and collapse
        // to a 2x2 box average, which is a genuine prefilter whose first
        // spectral null sits on the frequency that would otherwise fold onto
        // DC. Four taps per output pixel instead of Lanczos-3's ~144, and no
        // dedicated full-resolution filter pass. Clamp first so the sampler
        // never reaches past the border and darkens the edge.
        let smallOriginal = original.clampedToExtent()
            .transformed(by: CGAffineTransform(scaleX: s, y: s))
            .cropped(to: smallExtent)

        // Background-only blur, so the subject's (often bright) colour never
        // bleeds outward and halos the edge. Cut the subject out first,
        // transparent where the person is. Core Image blurs premultiplied, so
        // that hole contributes nothing and the background stays correctly
        // weighted. The plain full blur fills behind the subject, only ever
        // seen under the sharp subject, so no transparent gap shows.
        //
        // The cut-out is expressed with the subject mask directly -- transparent
        // as the foreground operand, the frame as the background operand --
        // which is algebraically identical to blending the frame over
        // transparency through an inverted mask but skips the inversion pass.
        let smallSigma = sigma * Double(s)
        let cut = CIFilter.blendWithMask()
        cut.inputImage = CIImage.empty()   // transparent where the subject is
        cut.backgroundImage = smallOriginal
        cut.maskImage = smallMask          // white = subject
        let bgCut = cut.outputImage ?? smallOriginal

        // Crop before clamping, so the clamp has a real edge to replicate and
        // the sigma-7 blur cannot suck transparency in from outside the frame
        // and thin the background in a border band. This matches the seed's
        // full-resolution behaviour.
        let blurredBg = bgCut.cropped(to: smallExtent)
            .clampedToExtent()
            .applyingGaussianBlur(sigma: smallSigma)
            .cropped(to: smallExtent)
        let fill = smallOriginal.clampedToExtent()
            .applyingGaussianBlur(sigma: smallSigma)
            .cropped(to: smallExtent)
        let smallBackground = blurredBg.composited(over: fill)

        // Back to full resolution, again with a plain affine. Both colour and
        // alpha here have just been through a sigma-7 Gaussian, so there is
        // essentially no energy left above the half-res Nyquist for bicubic's
        // wider kernel to recover: bilinear reconstructs the same surface for a
        // quarter of the taps, at the resolution where taps are most expensive.
        // Clamp before the transform so the 2x sampler has real edge values.
        let background = smallBackground.clampedToExtent()
            .transformed(by: CGAffineTransform(scaleX: 1.0 / s, y: 1.0 / s))
            .cropped(to: extent)

        let blend = CIFilter.blendWithMask()
        blend.inputImage = original          // sharp subject
        blend.backgroundImage = background   // halo-free blurred background
        blend.maskImage = mask               // white = subject
        return blend.outputImage ?? original
    }
}
// EVOLVE-BLOCK-END
