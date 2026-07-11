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
    # Stage Studio's current settings, hardware H.264 on the media engine,
    # capped rate with a 2 second bufsize window and a 2 second keyframe
    # interval, video range tagged for RTMP ingest.
    return [
        "-c:v", "h264_videotoolbox",
        "-realtime", "1",
        "-allow_sw", "1",
        "-b:v", "12000k",
        "-maxrate", "12000k",
        "-bufsize", "24000k",
        "-g", "60",
        "-pix_fmt", "yuv420p",
        "-color_range", "tv",
        "-fps_mode", "cfr",
    ]
# EVOLVE-BLOCK-END
