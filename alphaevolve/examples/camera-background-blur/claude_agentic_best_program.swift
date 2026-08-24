// blurlab candidate. Same visual pipeline as the seed with the wasted work
// removed.
//
//  1. Vision person segmentation runs on one frame in four, not every frame.
//     It is ~60% of the seed's per-frame cost, and the subject moves well
//     under a mask pixel in 1/30 s.
//  2. The feather runs at half resolution with half the sigma instead of on
//     the full-resolution upscaled mask, and it is cached along with the
//     segmentation, so it costs nothing on a frame that reuses the mask.
//  3. Both Gaussian passes run on a quarter-resolution copy with sigma scaled
//     to match. A sigma-14 blur keeps nothing that a 4x downsample throws
//     away, and the final blend samples the small result back up for free.
//  4. Nothing is upscaled into its own pass: the affine scale-ups fold into
//     the samplers of the blend that consumes them.

import CoreImage
import CoreImage.CIFilterBuiltins
import Vision

// EVOLVE-BLOCK-START
final class EvolvedBlurKernel {

    private let segmentationRequest: VNGeneratePersonSegmentationRequest = {
        let request = VNGeneratePersonSegmentationRequest()
        request.qualityLevel = .balanced
        request.outputPixelFormat = kCVPixelFormatType_OneComponent8
        return request
    }()

    // Feathered mask at half resolution, reused between segmentation frames.
    private var cachedMask: CIImage?
    private var cachedExtent: CGRect = .null

    private static let segmentEvery = 4      // Vision runs on 1 frame in 4.
    private static let maskScale: CGFloat = 0.5   // feather resolution
    private static let blurScale: CGFloat = 0.25  // background blur resolution
    private static let sigma: Double = 14
    private static let featherSigma: Double = 3

    // Person-segmented background blur for the webcam. Returns the original
    // frame if the Vision request fails. frameIndex counts up from 0
    // and frames arrive in order, so state kept between calls (for example a
    // cached mask) is valid.
    func process(_ pixelBuffer: CVPixelBuffer, frameIndex: Int, ciContext: CIContext) -> CIImage {
        let original = CIImage(cvPixelBuffer: pixelBuffer)
        let extent = original.extent

        let maskW = (extent.width * Self.maskScale).rounded()
        let maskH = (extent.height * Self.maskScale).rounded()
        let maskRect = CGRect(x: extent.minX, y: extent.minY, width: maskW, height: maskH)

        // Half-resolution feathered mask. Recomputed only when segmentation
        // runs, so both the Vision pass and the feather blur are off the
        // per-frame path three frames out of four.
        let maskSmall: CIImage
        if let cached = cachedMask, cachedExtent == extent,
           frameIndex % Self.segmentEvery != 0 {
            maskSmall = cached
        } else {
            let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, options: [:])
            guard (try? handler.perform([segmentationRequest])) != nil,
                  let maskBuffer = segmentationRequest.results?.first?.pixelBuffer else {
                return original
            }
            let raw = CIImage(cvPixelBuffer: maskBuffer)
            var m = raw.transformed(by: CGAffineTransform(
                scaleX: maskW / max(raw.extent.width, 1),
                y: maskH / max(raw.extent.height, 1)))
            // Feather the upscaled mask so the sharp-to-blurred boundary is a
            // soft gradient rather than the stair-stepped edge a low-res
            // segmentation mask gives when scaled up. Half the resolution with
            // half the sigma is the same gradient in frame space for a quarter
            // of the pixels.
            m = m.clampedToExtent()
                .applyingGaussianBlur(sigma: Self.featherSigma * Double(Self.maskScale))
                .cropped(to: maskRect)
                .insertingIntermediate(cache: true)
            maskSmall = m
            cachedMask = m
            cachedExtent = extent
        }
        // Scale-ups are pure samplers, Core Image folds them into the blend
        // below rather than rendering an upscaled copy.
        let mask = maskSmall.transformed(by: CGAffineTransform(
            scaleX: extent.width / maskW, y: extent.height / maskH))

        let blurW = (extent.width * Self.blurScale).rounded()
        let blurH = (extent.height * Self.blurScale).rounded()
        let blurRect = CGRect(x: extent.minX, y: extent.minY, width: blurW, height: blurH)
        let sigma = Self.sigma * Double(Self.blurScale)
        let source = original
            .transformed(by: CGAffineTransform(scaleX: blurW / extent.width,
                                               y: blurH / extent.height))
            .cropped(to: blurRect)
        let maskBlurRes = maskSmall.transformed(by: CGAffineTransform(
            scaleX: blurW / maskW, y: blurH / maskH))

        // Background-only blur, so the subject's (often bright) colour never
        // bleeds outward and halos the edge. Cut the subject out first,
        // transparent where the person is. Core Image blurs premultiplied, so
        // that hole contributes nothing and the background stays correctly
        // weighted. A plain full blur fills behind the subject, only ever seen
        // under the sharp subject, never at the edge, so no transparent gap
        // shows.
        let bgCoverage = maskBlurRes.applyingFilter("CIColorInvert")
        let bgCut = source.applyingFilter("CIBlendWithMask", parameters: [
            kCIInputBackgroundImageKey: CIImage.empty(),
            kCIInputMaskImageKey: bgCoverage
        ])
        let blurredBg = bgCut.clampedToExtent().applyingGaussianBlur(sigma: sigma).cropped(to: blurRect)
        let fill = source.clampedToExtent().applyingGaussianBlur(sigma: sigma).cropped(to: blurRect)
        let background = blurredBg.composited(over: fill)
            .transformed(by: CGAffineTransform(scaleX: extent.width / blurW,
                                               y: extent.height / blurH))

        let blend = CIFilter.blendWithMask()
        blend.inputImage = original          // sharp subject
        blend.backgroundImage = background   // halo-free blurred background
        blend.maskImage = mask               // white = subject
        return blend.outputImage ?? original
    }
}
// EVOLVE-BLOCK-END
