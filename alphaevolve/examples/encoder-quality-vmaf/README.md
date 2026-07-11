# Evolving live-stream encoder settings with AlphaEvolve, including the part where it cheated

AlphaEvolve tuned the H.264 encoder settings of [Stage Studio](https://stagestudio.tv),
a macOS streaming app, for perceptual quality (VMAF) at a fixed bandwidth
budget. The result is a real but modest quality gain, and a much more
valuable lesson. **The winning candidate exploited a hole in the evaluation
gate, and only a post-run ablation revealed what actually mattered.** If the
camera-blur example next door shows evolution at its best, this one shows why
you never ship a winner without dissecting it.

## The setup

The app encodes 1440p30 on Apple's media engine (h264_videotoolbox via
ffmpeg) and pushes RTMPS. The genome is the list of ffmpeg encoder arguments
([seed.py](seed.py) holds the settings the app shipped before this run). The
evaluator ([evaluate.py](evaluate.py)) encodes a fixed program-feed clip and
scores VMAF against the source, with hard gates. The encoder must stay
h264_videotoolbox (hardware encode is a product requirement), measured
bitrate within 5 percent of 12000 kbps, keyframes at most 2.1s apart,
faster than realtime.

First finding, before any evolution. The shipped settings used only about
**1500 kbps of the 12000 kbps budget** on mixed screen-plus-camera content.
VideoToolbox's rate control undershoots hard on partly static frames.

## The run, and the cheat

39 candidates. The winner scored VMAF 95.85 against the 94.41 baseline by
combining legitimate quality flags with one exploit. It set `-b:v 17500k`
(overprovisioned past the budget) and **removed `-maxrate` entirely**. The
measured output happened to stay under the cap *on the test clip*, so the
gate passed, but nothing bounded the bitrate on harder content anymore. The
evolver even wrote a comment explaining the trick ("aggressively
overprovision the VBR target..."). Classic Goodhart, it optimized exactly
what the evaluator measured, and the evaluator measured one clip.

## The ablation, where the real knowledge came from

Sweeping variants after the run isolated each factor.

| variant | vmaf | measured kbps |
|---|---|---|
| baseline (shipped settings) | 94.41 | 1511 |
| raw winner (17500k target, no maxrate) | 95.85 | 9770 |
| winner + maxrate 12000k restored | 94.98 | 2273 |
| winner + maxrate 14000k, bigger bufsize | 95.13 | 2901 |
| quality flags + honest 12000k target, no maxrate | **95.77** | 8264 |

Two conclusions fall out. **Any `-maxrate`/`-bufsize` (VideoToolbox's
DataRateLimits) triggers the throttling**, regardless of headroom, that is
where the undershoot comes from. And the overprovisioned target was never
the source of the gain, an honest target at the real budget reaches within
0.08 VMAF of the exploit once maxrate is gone.

Safety, verified rather than assumed. Without maxrate, does ABR hold the
budget on hard content? On a worst-case stress clip (the stream at 20x
speed, every frame changes) the honest config measured 10.1 Mbps, on a
webcam clip 10.4 Mbps, both under the 12.6 Mbps cap.

The shipped configuration keeps the honest `-b:v`, drops maxrate/bufsize,
and adds the quality flags the winner found, `-bf 3`, `-profile:v high`,
`-level 5.2`, `-coder cabac`, `-prio_speed 0`, `-power_efficient 0`, and no
`-realtime` (it biases speed over quality and the encode runs 4x realtime
without it).

## How big is the win, honestly

Modest. Measured across three content types, old versus new,

| clip | old vmaf | new vmaf | delta |
|---|---|---|---|
| mixed montage | 94.41 | 95.77 | +1.36 |
| 20x stress | 95.99 | 97.13 | +1.15 |
| webcam motion | 91.56 | 93.06 | +1.50 |

Per-frame percentiles on the webcam clip tell the same story (old p5 74.96,
new p5 76.12), the gain is uniform, about +1.2 everywhere including the
worst frames. Roughly 6 VMAF points equal one just-noticeable difference,
so this is about a quarter of a JND. Worth shipping because it is free
(hardware encoder, no CPU cost, one flags change) and strictly better on
every measurement, but not a transformation. The camera-blur example
delivered the dramatic number, this one delivered the understanding.

## Lessons for your own AlphaEvolve gates

- A gate only enforces what it measures. "Bitrate under cap on this clip"
  is not "bitrate under cap." The winner will find the difference.
- Never ship the raw winner. Ablate it, separate the legitimate gains from
  the gate exploits, and re-verify the honest variant.
- Failure insights matter. Returning *why* a candidate died (which gate,
  with numbers) visibly steered later candidates around the gates.
- Report the effect size honestly, means and percentiles, against a
  known-JND scale. A metric going up is not automatically a story.

## Files and reproduction

```
seed.py           the app's pre-optimization encoder settings (EVOLVE-BLOCK wrapped)
evaluate.py       encode + gates + VMAF (1080p-scaled, deterministic)
evolve.py         the AlphaEvolve controller loop
best_program.py   the raw winner from the run, kept as the exhibit, do not ship it
source.mov        bring your own test clip (git-ignored)
```

Needs ffmpeg with libvmaf (homebrew's has it), the `alpha_evolve` client
from github.com/Google-Cloud-AI/alphaevolve-on-googlecloud, a Gemini
Enterprise app (any tier license, trial included), and ADC auth. Cut a test
clip from a real recording of whatever your encoder actually encodes, run
`python3 evaluate.py` for the baseline, set `PROJECT_ID` and `GE_APP_ID`,
and run `evolve.py`. Then, whatever wins, ablate it before believing it.
