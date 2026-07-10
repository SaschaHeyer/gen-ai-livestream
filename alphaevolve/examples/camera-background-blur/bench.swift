// blurlab bench harness. Runs the EvolvedBlurKernel (from the file compiled
// next to this one, seed.swift or a candidate) over a fixed webcam clip and
// reports how fast it ran and how close its output is to the golden frames.
//
// Golden mode, render the reference output once and save it.
//   bench --clip clip.mov --frames 60 --write-golden goldens
// Eval mode, score a candidate against the goldens.
//   bench --clip clip.mov --frames 60 --golden goldens
// Synthetic mode replaces the clip with generated frames. No person is in
// them, so Vision yields an all-background mask and the whole frame blurs.
// Use it only to smoke-test the harness, never to evolve.
//
// Output is one JSON object on stdout, msPerFrame is the median.

import AVFoundation
import CoreImage
import CoreImage.CIFilterBuiltins
import Metal

@main
struct Bench {

    static func main() {
        var clipPath: String?
        var goldenDir: String?
        var writeGoldenDir: String?
        var maxFrames = 60
        var warmup = 3
        var synthetic = false

        var args = Array(CommandLine.arguments.dropFirst())
        while !args.isEmpty {
            let arg = args.removeFirst()
            switch arg {
            case "--clip": clipPath = args.isEmpty ? nil : args.removeFirst()
            case "--golden": goldenDir = args.isEmpty ? nil : args.removeFirst()
            case "--write-golden": writeGoldenDir = args.isEmpty ? nil : args.removeFirst()
            case "--frames": maxFrames = Int(args.removeFirst()) ?? 60
            case "--warmup": warmup = Int(args.removeFirst()) ?? 3
            case "--synthetic": synthetic = true
            default: fail("unknown argument \(arg)")
            }
        }

        let frames: [CVPixelBuffer]
        if synthetic {
            frames = makeSyntheticFrames(count: maxFrames)
        } else if let clipPath {
            frames = loadClip(URL(fileURLWithPath: clipPath), maxFrames: maxFrames)
        } else {
            fail("pass --clip <file> or --synthetic")
        }
        guard !frames.isEmpty else { fail("no frames decoded") }

        let width = CVPixelBufferGetWidth(frames[0])
        let height = CVPixelBufferGetHeight(frames[0])

        let ciContext: CIContext
        if let device = MTLCreateSystemDefaultDevice() {
            ciContext = CIContext(mtlDevice: device)
        } else {
            ciContext = CIContext()
        }

        let kernel = EvolvedBlurKernel()
        guard let output = makeBuffer(width: width, height: height) else {
            fail("could not allocate output buffer")
        }

        // Warm up so shader compilation and the first Vision model load do
        // not pollute the timing.
        for _ in 0..<warmup {
            let image = kernel.process(frames[0], frameIndex: 0, ciContext: ciContext)
            ciContext.render(image, to: output)
        }

        var times: [Double] = []
        var ssims: [Double] = []
        let goldenURL = goldenDir.map { URL(fileURLWithPath: $0) }
        let writeURL = writeGoldenDir.map { URL(fileURLWithPath: $0) }
        if let writeURL {
            try? FileManager.default.createDirectory(at: writeURL, withIntermediateDirectories: true)
        }

        for (index, frame) in frames.enumerated() {
            let start = CFAbsoluteTimeGetCurrent()
            let image = kernel.process(frame, frameIndex: index, ciContext: ciContext)
            ciContext.render(image, to: output)
            times.append((CFAbsoluteTimeGetCurrent() - start) * 1000)

            if let writeURL {
                writePNG(output, to: writeURL.appendingPathComponent(frameName(index)), context: ciContext)
            }
            if let goldenURL {
                let path = goldenURL.appendingPathComponent(frameName(index))
                guard let golden = loadPNG(path, context: ciContext) else {
                    fail("missing golden frame \(path.path), re-run --write-golden with the same clip and frame count")
                }
                guard CVPixelBufferGetWidth(golden) == width, CVPixelBufferGetHeight(golden) == height else {
                    fail("golden frame size does not match the clip, re-render the goldens")
                }
                ssims.append(ssim(output, golden))
            }
        }

        let median = times.sorted()[times.count / 2]
        var result: [String: Any] = [
            "frames": frames.count,
            "width": width,
            "height": height,
            "msPerFrame": round3(median),
            "msMean": round3(times.reduce(0, +) / Double(times.count)),
        ]
        if !ssims.isEmpty {
            result["ssim"] = round5(ssims.reduce(0, +) / Double(ssims.count))
            result["ssimMin"] = round5(ssims.min() ?? 0)
        }
        if let writeURL {
            let manifest: [String: Any] = [
                "frames": frames.count, "width": width, "height": height,
                "msPerFrame": round3(median),
            ]
            let data = try! JSONSerialization.data(withJSONObject: manifest, options: [.sortedKeys])
            try? data.write(to: writeURL.appendingPathComponent("manifest.json"))
        }
        let data = try! JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
        print(String(data: data, encoding: .utf8)!)
    }

    // MARK: - Clip loading

    static func loadClip(_ url: URL, maxFrames: Int) -> [CVPixelBuffer] {
        let asset = AVURLAsset(url: url)
        guard let track = asset.tracks(withMediaType: .video).first,
              let reader = try? AVAssetReader(asset: asset) else {
            fail("could not open \(url.path)")
        }
        let output = AVAssetReaderTrackOutput(track: track, outputSettings: [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA
        ])
        reader.add(output)
        reader.startReading()
        var frames: [CVPixelBuffer] = []
        while frames.count < maxFrames, let sample = output.copyNextSampleBuffer() {
            // Deep-copy each frame. The reader recycles its buffers from a
            // small pool, holding them would stall decoding.
            if let source = CMSampleBufferGetImageBuffer(sample), let copy = deepCopy(source) {
                frames.append(copy)
            }
        }
        return frames
    }

    static func deepCopy(_ source: CVPixelBuffer) -> CVPixelBuffer? {
        let width = CVPixelBufferGetWidth(source)
        let height = CVPixelBufferGetHeight(source)
        guard let copy = makeBuffer(width: width, height: height) else { return nil }
        CVPixelBufferLockBaseAddress(source, .readOnly)
        CVPixelBufferLockBaseAddress(copy, [])
        defer {
            CVPixelBufferUnlockBaseAddress(copy, [])
            CVPixelBufferUnlockBaseAddress(source, .readOnly)
        }
        guard let src = CVPixelBufferGetBaseAddress(source),
              let dst = CVPixelBufferGetBaseAddress(copy) else { return nil }
        let srcStride = CVPixelBufferGetBytesPerRow(source)
        let dstStride = CVPixelBufferGetBytesPerRow(copy)
        for row in 0..<height {
            memcpy(dst + row * dstStride, src + row * srcStride, min(srcStride, dstStride))
        }
        return copy
    }

    static func makeBuffer(width: Int, height: Int) -> CVPixelBuffer? {
        var buffer: CVPixelBuffer?
        CVPixelBufferCreate(nil, width, height, kCVPixelFormatType_32BGRA,
                            [kCVPixelBufferIOSurfacePropertiesKey: [:]] as CFDictionary, &buffer)
        return buffer
    }

    // MARK: - Synthetic frames (harness smoke test only)

    static func makeSyntheticFrames(count: Int) -> [CVPixelBuffer] {
        let width = 1280, height = 720
        let ciContext = CIContext()
        var frames: [CVPixelBuffer] = []
        for index in 0..<count {
            let gradient = CIFilter.linearGradient()
            gradient.point0 = CGPoint(x: 0, y: 0)
            gradient.point1 = CGPoint(x: CGFloat(width), y: CGFloat(height))
            gradient.color0 = CIColor(red: 0.15, green: 0.12, blue: 0.25)
            gradient.color1 = CIColor(red: 0.55, green: 0.35, blue: 0.30)
            let dot = CIFilter.radialGradient()
            let t = CGFloat(index) / CGFloat(max(count - 1, 1))
            dot.center = CGPoint(x: 200 + t * CGFloat(width - 400), y: CGFloat(height) / 2)
            dot.radius0 = 60
            dot.radius1 = 140
            dot.color0 = CIColor(red: 0.9, green: 0.85, blue: 0.7)
            dot.color1 = CIColor(red: 0.9, green: 0.85, blue: 0.7, alpha: 0)
            // Sharp high-frequency detail so a blur measurably lowers SSIM.
            // Smooth gradients alone stay near-identical under a blur, which
            // would let a visually wrong candidate pass the smoke test.
            let checker = CIFilter.checkerboardGenerator()
            checker.width = 6
            checker.sharpness = 1
            checker.color0 = CIColor(red: 0.1, green: 0.1, blue: 0.1, alpha: 0.35)
            checker.color1 = CIColor(red: 0.9, green: 0.9, blue: 0.9, alpha: 0.35)
            let image = dot.outputImage!
                .composited(over: checker.outputImage!)
                .composited(over: gradient.outputImage!)
                .cropped(to: CGRect(x: 0, y: 0, width: width, height: height))
            guard let buffer = makeBuffer(width: width, height: height) else { continue }
            ciContext.render(image, to: buffer)
            frames.append(buffer)
        }
        return frames
    }

    // MARK: - PNG io

    static func frameName(_ index: Int) -> String {
        String(format: "frame-%04d.png", index)
    }

    static func writePNG(_ buffer: CVPixelBuffer, to url: URL, context: CIContext) {
        let image = CIImage(cvPixelBuffer: buffer)
        let colorSpace = CGColorSpace(name: CGColorSpace.sRGB)!
        guard let data = context.pngRepresentation(of: image, format: .BGRA8, colorSpace: colorSpace) else {
            fail("could not encode \(url.lastPathComponent)")
        }
        try? data.write(to: url)
    }

    static func loadPNG(_ url: URL, context: CIContext) -> CVPixelBuffer? {
        guard let image = CIImage(contentsOf: url) else { return nil }
        let width = Int(image.extent.width), height = Int(image.extent.height)
        guard let buffer = makeBuffer(width: width, height: height) else { return nil }
        context.render(image, to: buffer)
        return buffer
    }

    // MARK: - SSIM

    // Grayscale SSIM over non-overlapping 8x8 windows, the standard constants
    // for 8-bit dynamic range. Enough precision to gate visual identity.
    static func ssim(_ a: CVPixelBuffer, _ b: CVPixelBuffer) -> Double {
        guard let lumaA = luma(a), let lumaB = luma(b) else { return 0 }
        let width = CVPixelBufferGetWidth(a)
        let height = CVPixelBufferGetHeight(a)
        let c1 = 6.5025, c2 = 58.5225
        let window = 8
        var total = 0.0
        var windows = 0
        var y = 0
        while y + window <= height {
            var x = 0
            while x + window <= width {
                var sumA = 0.0, sumB = 0.0, sumAA = 0.0, sumBB = 0.0, sumAB = 0.0
                for wy in 0..<window {
                    let row = (y + wy) * width + x
                    for wx in 0..<window {
                        let va = lumaA[row + wx], vb = lumaB[row + wx]
                        sumA += va; sumB += vb
                        sumAA += va * va; sumBB += vb * vb; sumAB += va * vb
                    }
                }
                let n = Double(window * window)
                let muA = sumA / n, muB = sumB / n
                let varA = sumAA / n - muA * muA
                let varB = sumBB / n - muB * muB
                let cov = sumAB / n - muA * muB
                let numerator = (2 * muA * muB + c1) * (2 * cov + c2)
                let denominator = (muA * muA + muB * muB + c1) * (varA + varB + c2)
                total += numerator / denominator
                windows += 1
                x += window
            }
            y += window
        }
        return windows > 0 ? total / Double(windows) : 0
    }

    static func luma(_ buffer: CVPixelBuffer) -> [Double]? {
        let width = CVPixelBufferGetWidth(buffer)
        let height = CVPixelBufferGetHeight(buffer)
        CVPixelBufferLockBaseAddress(buffer, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(buffer, .readOnly) }
        guard let base = CVPixelBufferGetBaseAddress(buffer) else { return nil }
        let stride = CVPixelBufferGetBytesPerRow(buffer)
        var result = [Double](repeating: 0, count: width * height)
        let bytes = base.assumingMemoryBound(to: UInt8.self)
        for y in 0..<height {
            let row = y * stride
            for x in 0..<width {
                let p = row + x * 4
                let blue = Double(bytes[p]), green = Double(bytes[p + 1]), red = Double(bytes[p + 2])
                result[y * width + x] = 0.299 * red + 0.587 * green + 0.114 * blue
            }
        }
        return result
    }

    // MARK: - Helpers

    static func round3(_ value: Double) -> Double { (value * 1000).rounded() / 1000 }
    static func round5(_ value: Double) -> Double { (value * 100000).rounded() / 100000 }

    static func fail(_ message: String) -> Never {
        FileHandle.standardError.write(("blurlab bench error, " + message + "\n").data(using: .utf8)!)
        exit(1)
    }
}
