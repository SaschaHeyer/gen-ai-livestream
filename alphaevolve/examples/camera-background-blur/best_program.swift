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
    
    private let sequenceHandler = VNSequenceRequestHandler()
    private var cachedMask: CIImage?
    private var cachedMaskSmall: CIImage?

    // Person-segmented background blur for the webcam. Returns the original
    // frame if the Vision request fails. frameIndex counts up from 0
    // and frames arrive in order, so state kept between calls (for example a
    // cached mask) is valid.
    func process(_ pixelBuffer: CVPixelBuffer, frameIndex: Int, ciContext: CIContext) -> CIImage {
        let original = CIImage(cvPixelBuffer: pixelBuffer)
        let scaleFactor: CGFloat = 0.25
        
        if frameIndex % 3 == 0 || cachedMask == nil {
            if (try? sequenceHandler.perform([segmentationRequest], on: pixelBuffer)) != nil,
               let maskBuffer = segmentationRequest.results?.first?.pixelBuffer {
                let rawMask = CIImage(cvPixelBuffer: maskBuffer)
                
                let sx = original.extent.width / max(rawMask.extent.width, 1)
                let sy = original.extent.height / max(rawMask.extent.height, 1)
                
                let fullMask = rawMask.transformed(by: CGAffineTransform(scaleX: sx, y: sy))
                    .clampedToExtent()
                    .applyingGaussianBlur(sigma: 3)
                    .cropped(to: original.extent)
                
                let smallMask = rawMask.transformed(by: CGAffineTransform(scaleX: sx * scaleFactor, y: sy * scaleFactor))
                    .clampedToExtent()
                    .applyingGaussianBlur(sigma: 3 * scaleFactor)
                    .cropped(to: CGRect(x: 0, y: 0, width: original.extent.width * scaleFactor, height: original.extent.height * scaleFactor))
                
                cachedMask = fullMask
                cachedMaskSmall = smallMask
            }
        }
        
        guard let finalMask = cachedMask, let maskSmall = cachedMaskSmall else {
            return original
        }

        let sigma: Double = 14.0
        let scaledSigma = sigma * Double(scaleFactor)

        let lowResSize = CGAffineTransform(scaleX: scaleFactor, y: scaleFactor)
        let originalSmall = original.transformed(by: lowResSize)

        let bgCoverageSmall = maskSmall.applyingFilter("CIColorInvert")
        let bgCutSmall = originalSmall.applyingFilter("CIBlendWithMask", parameters: [
            kCIInputBackgroundImageKey: CIImage.empty(),
            kCIInputMaskImageKey: bgCoverageSmall
        ])

        let blurredBgSmall = bgCutSmall.clampedToExtent().applyingGaussianBlur(sigma: scaledSigma).cropped(to: originalSmall.extent)
        let fillSmall = originalSmall.clampedToExtent().applyingGaussianBlur(sigma: scaledSigma).cropped(to: originalSmall.extent)
        let backgroundSmall = blurredBgSmall.composited(over: fillSmall)

        let background = backgroundSmall
            .transformed(by: CGAffineTransform(scaleX: 1.0 / scaleFactor, y: 1.0 / scaleFactor))

        let blend = CIFilter.blendWithMask()
        blend.inputImage = original
        blend.backgroundImage = background
        blend.maskImage = finalMask
        return blend.outputImage ?? original
    }
}
// EVOLVE-BLOCK-END
