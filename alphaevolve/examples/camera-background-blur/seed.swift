// blurlab seed program. A faithful copy of SceneCompositor.blurredCamera,
// wrapped as a stateful kernel so an evolved version may cache work across
// frames. AlphaEvolve mutates only the region between the EVOLVE-BLOCK
// markers. The class name and the process signature must not change, the
// bench harness instantiates EvolvedBlurKernel and calls process once per
// frame in order.

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

    // Person-segmented background blur for the webcam. Returns the original
    // frame if the Vision request fails. frameIndex counts up from 0
    // and frames arrive in order, so state kept between calls (for example a
    // cached mask) is valid.
    func process(_ pixelBuffer: CVPixelBuffer, frameIndex: Int, ciContext: CIContext) -> CIImage {
        let original = CIImage(cvPixelBuffer: pixelBuffer)
        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, options: [:])
        guard (try? handler.perform([segmentationRequest])) != nil,
              let maskBuffer = segmentationRequest.results?.first?.pixelBuffer else {
            return original
        }
        var mask = CIImage(cvPixelBuffer: maskBuffer)
        let sx = original.extent.width / max(mask.extent.width, 1)
        let sy = original.extent.height / max(mask.extent.height, 1)
        mask = mask.transformed(by: CGAffineTransform(scaleX: sx, y: sy))
        // Feather the upscaled mask so the sharp-to-blurred boundary is a soft
        // gradient rather than the stair-stepped edge a low-res segmentation
        // mask gives when scaled up.
        mask = mask.clampedToExtent()
            .applyingGaussianBlur(sigma: 3)
            .cropped(to: original.extent)

        let sigma: Double = 14
        // Background-only blur, so the subject's (often bright) colour never
        // bleeds outward and halos the edge. Cut the subject out first,
        // transparent where the person is. Core Image blurs premultiplied, so
        // that hole contributes nothing and the background stays correctly
        // weighted. A plain full blur fills behind the subject, only ever seen
        // under the sharp subject, never at the edge, so no transparent gap
        // shows.
        let bgCoverage = mask.applyingFilter("CIColorInvert")
        let bgCut = original.applyingFilter("CIBlendWithMask", parameters: [
            kCIInputBackgroundImageKey: CIImage.empty(),
            kCIInputMaskImageKey: bgCoverage
        ])
        let blurredBg = bgCut.clampedToExtent().applyingGaussianBlur(sigma: sigma).cropped(to: original.extent)
        let fill = original.clampedToExtent().applyingGaussianBlur(sigma: sigma).cropped(to: original.extent)
        let background = blurredBg.composited(over: fill)

        let blend = CIFilter.blendWithMask()
        blend.inputImage = original          // sharp subject
        blend.backgroundImage = background   // halo-free blurred background
        blend.maskImage = mask               // white = subject
        return blend.outputImage ?? original
    }
}
// EVOLVE-BLOCK-END
