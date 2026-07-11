# encoderlab seed program. The exact video encoder settings Stage Studio
# ships today in FFmpegStreamer (1440p30 ladder step, 12000 kbps). AlphaEvolve
# mutates only the region between the EVOLVE-BLOCK markers. encoder_args()
# must keep returning a flat list of ffmpeg output arguments, the evaluator
# appends them to a fixed input and output.
#
# Hard rules enforced by the evaluator, not up for negotiation. The encoder
# must be h264_videotoolbox (the app encodes on the media engine, software
# encoders would win the metric and lose the product). The measured output
# bitrate must stay within 5 percent of 12000 kbps. Keyframes at most 2.1
# seconds apart (platform ingest rules). Encode faster than realtime.

# EVOLVE-BLOCK-START
def encoder_args():
    # Aggressively overprovision the VBR target to trick VideoToolbox into fully utilizing
    # the 12000 kbps budget. Previous tests showed strict maxrate/bufsize causes severe throttling.
    # Push B-frames to 3 and explicitly unlock Level 5.2 for maximum internal DPB limits.
    return [
        "-c:v", "h264_videotoolbox",
        "-b:v", "17500k",
        "-g", "60",
        "-bf", "3",
        "-profile:v", "high",
        "-level", "5.2",
        "-coder", "cabac",
        "-prio_speed", "0",
        "-power_efficient", "0",
        "-color_range", "tv",
        "-colorspace", "bt709",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-fps_mode", "cfr",
        "-pix_fmt", "yuv420p",
    ]
# EVOLVE-BLOCK-END
