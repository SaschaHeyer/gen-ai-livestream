"""The optimization brief, shared by every runner in this folder.

Both runners import this so the AlphaEvolve backend and Claude Code are
handed byte-identical instructions. Any head-to-head number in the README
depends on that, so keep the text here and never inline a copy.
"""

PROBLEM = """\
Optimize a macOS Core Image + Vision webcam background blur kernel written
in Swift. The kernel runs inside a 30fps live streaming render loop, so
milliseconds per frame matter. The current implementation runs Vision
person segmentation and two full-resolution Gaussian blurs on every frame.

The primary metric is speedup (baseline ms per frame divided by candidate
ms per frame, higher is better). A hard SSIM gate rejects any candidate
whose output differs visibly from the reference (score -1e12), so quality
can not be traded away, only wasted work can be removed. The ssim metric
is reported alongside for context.

Constraints. Keep the class named EvolvedBlurKernel and the exact process
signature. Frames arrive in order with frameIndex counting from 0, and the
instance persists across the whole clip, so caching state between frames
(for example reusing the segmentation mask for a few frames, or blurring
at reduced resolution and scaling sigma to match) is allowed and
encouraged. The code must compile with swiftc on macOS using only
CoreImage, Vision, and Foundation. Preserve the guard that returns the
original frame when the Vision request fails.

Ideas worth exploring. Run segmentation every Nth frame and reuse the
mask. Blur a downscaled copy and upscale (rescale sigma accordingly).
Collapse the two Gaussian passes into one. Cheaper mask feathering.
Avoid clampedToExtent where a crop suffices.
"""
