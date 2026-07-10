# Evolving a real-time webcam background blur with AlphaEvolve

AlphaEvolve made the webcam background blur of a shipping macOS app
**3.4x faster with visually identical output**, in a single evolution run,
judged entirely by an automated evaluator on my Mac.

This folder is the complete, reproducible experiment. The optimization target
is real production code from [Stage Studio](https://stagestudio.tv), a native
macOS streaming studio. Its compositor blurs the room behind you on the webcam
(person segmentation plus background blur) inside a 30fps render loop, and
that one function was the most expensive per-frame path in the app.

| | before (production code) | after (evolved) |
|---|---|---|
| cost per frame (1080p, M-series) | 17.95 ms | 5.26 ms |
| share of the 33 ms frame budget at 30fps | 54% | 16% |
| similarity to reference output (SSIM) | 1.0 (it is the reference) | 0.99833 |
| candidates evaluated | | 10 |
| human judgment during the run | | none |

The recorded speedup during the run peaked at 5.41x. Wall-clock timing is
noisy, independent re-runs land between 2.8x and 5.4x, so the honest headline
is the clean-run median, 3.4x.

## What AlphaEvolve is (and the one thing people get wrong)

AlphaEvolve is DeepMind's evolutionary coding agent, generally available on
the Gemini Enterprise Agent Platform since July 2026. You give it two things.

1. **A seed program.** Working code, with the region it may rewrite wrapped in
   `EVOLVE-BLOCK-START` / `EVOLVE-BLOCK-END` comment markers.
2. **An evaluator.** A deterministic function that you run on your own
   machine. It receives each mutated candidate, executes it however you like,
   and returns one or more scalar scores, higher is better.

The backend proposes mutated candidates (Gemini models generate them, guided
by the scores of earlier candidates), your controller loop evaluates them
locally and reports the numbers back, and selection pressure does the rest.

The thing people get wrong. **AlphaEvolve never sees your output.** It cannot
look at a frame or listen to audio. It only reads the numbers your evaluator
returns. The entire craft of an experiment like this is turning a subjective
goal ("the blur still looks good but runs faster") into numbers that cannot be
gamed. If your metric has a loophole, evolution will find the loophole,
not the optimization.

Also worth knowing, the tooling is Python-first and the docs demonstrate
Python, Rust, and C++. This experiment evolves **Swift**, which works fine
because evaluation is fully client-side. The evaluator compiles each candidate
with `swiftc` and runs it. Any language you can compile and score works.

## The optimization target

The seed ([seed.swift](seed.swift)) is a faithful copy of Stage Studio's
`blurredCamera`. Every frame, at full 1920x1080, it did all of this.

```
Vision person segmentation                  find the person
mask feather (Gaussian, sigma 3)            soften the mask edge
background cut + Gaussian blur (sigma 14)   full-res blur pass 1
fill layer   + Gaussian blur (sigma 14)     full-res blur pass 2
composite                                   sharp person over blurred room
```

17.95 ms per frame, more than half the frame budget of a 30fps loop, running
synchronously inside the render tick.

## The harness, an objective that cannot be gamed

Three pieces, all in this folder.

**[bench.swift](bench.swift)** compiles next to any candidate kernel and runs
it over a fixed webcam clip (60 frames), then prints JSON metrics. It measures
median milliseconds per frame (with warmup passes so shader compilation does
not pollute the timing) and SSIM against golden frames, both the mean and the
worst single frame.

**[evaluate.py](evaluate.py)** is the objective function. For each candidate
it writes the code, compiles it (`swiftc -O`, a few seconds), runs the bench,
and returns

```
speedup = baseline ms per frame / candidate ms per frame
ssim    = mean SSIM vs the golden frames
```

with a hard gate. Any candidate below SSIM 0.98 mean or 0.95 on its worst
frame gets the failure sentinel (-1e12) instead of a speedup. **Quality is a
rule, not a tradeoff.** The only way to score is to look identical and be
faster. Failed candidates also return an insight string (compile error versus
SSIM gate) so the evolver learns why, not just that, a candidate died.

**Golden frames** are rendered once by the seed itself on the same clip. The
reference is literally "whatever the current production code outputs," so
the target is visual equivalence with today's app, not some abstract ideal.

Two hard-won details worth stealing.

- **The clip must contain a person.** Vision returns an all-background mask
  when nobody is in frame, so on empty footage the seed blurs everything and
  a cheating candidate that blurs the whole frame without segmentation scores
  near-perfect SSIM. I caught this because my first "gate test" candidate
  passed when it should have failed. Synthetic frames are only good for
  smoke-testing the plumbing.
- **Keep evaluation concurrency low (2).** Candidates share one GPU, and the
  score is wall-clock. Parallel evaluations skew each other's timing.

## What evolution invented

The winning kernel ([best_program.swift](best_program.swift)) arrived after
10 candidates and combines three techniques.

**1. Segmentation every 3rd frame, cached in between.**

```swift
if frameIndex % 3 == 0 || cachedMask == nil {
    // run Vision, cache both a full-res and a quarter-res feathered mask
}
```

A person moves little in 66 ms, so a slightly stale mask is nearly free
quality-wise but amortizes the most expensive stage 3x. It also swapped
`VNImageRequestHandler` for `VNSequenceRequestHandler`, Vision's API for
video streams, an idea that was not in the prompt.

**2. The whole blur pipeline at quarter resolution.**

```swift
let scaleFactor: CGFloat = 0.25
let originalSmall = original.transformed(by: scale(0.25))   // 480x270
// both blur passes on the small image, sigma rescaled 14 -> 3.5
let background = backgroundSmall.transformed(by: scale(4.0)) // upscale back
```

1/16th of the pixels and 1/4 of the blur radius. A blurred background cannot
reveal upscaling artifacts, it is blurry by definition, which is why SSIM
barely moves.

**3. The full-resolution mask for the final composite.**

```swift
blend.inputImage = original          // sharp person, full res
blend.backgroundImage = background   // blurred room, computed small
blend.maskImage = fullResMask        // the edge stays crisp
```

Only the boundary between person and background needs full resolution, so
that is the only place that gets it.

None of these is exotic on its own. The point is that nobody wrote them, and
the specific combination (which cadence, which scale factor, where the full
res mask still matters) was found by search against a gate that made quality
regressions impossible.

## The run, candidate by candidate

Seed scores first, then the 10 candidates in order.

| candidate | speedup | ssim | note |
|---|---|---|---|
| seed | 0.86 | 1.000 | baseline sanity check, timing noise around 1.0 |
| 1 | 2.57 | 0.99889 | above the gate on the very first mutation |
| 2 | 4.17 | 0.99833 | |
| 3 | 2.24 | 0.99889 | |
| 4 | 4.53 | 0.99833 | |
| 5 | 4.22 | 0.99833 | |
| 6 | 5.29 | 0.99834 | |
| 7 | **5.41** | 0.99833 | the winner |
| 8 | 3.49 | 0.99833 | |
| 9 | 2.76 | 0.99875 | |
| 10 | 1.32 | 0.99927 | exploratory dud |

The backend idle-stopped the experiment at 10 of the requested 40 candidates
(it terminates after 120 seconds without traffic, and a Swift compile plus a
60-frame GPU benchmark per candidate is on the slow side). Ten were enough.

## How the result was verified

Three layers, each catching what the previous one cannot.

**1. The metric, all frames.** Every one of the 60 frames compared to the
production code's output. SSIM mean 0.99833, and the worst single frame also
had to clear its own floor, so no average could hide one bad frame. SSIM is
deterministic here, re-runs reproduce 0.99833 exactly.

**2. An amplified difference map of the worst frame.** Find the frame where
the two versions disagree most, subtract the images, multiply the error by 10
so invisible differences glow. The result is black almost everywhere. The
entire disagreement is a thin halo hugging the person's silhouette, exactly
the signature the 3-frame mask cache predicts (the edge lags movement by up
to 66 ms), and nothing else. Raw numbers, the average pixel across the clip
differs by 0.21 of 255, the worst frame by 0.46 of 255, and even the 99.9th
percentile pixel of the worst frame differs by 40 of 255, confined to an
edge band a few pixels wide. This check matters because it does not just
measure the error, it locates and explains it.

**3. Eyes, on the worst case.** Side-by-side of that same worst frame,
indistinguishable at viewing size, and this is the most-different frame in
the clip by construction.

Known limits, stated plainly. The timing metric is wall-clock and noisy
(2.8x to 5.4x across re-runs, quality is exact but speed is a range). And
the whole run was scored on one short clip of a person sitting fairly still.
The mask cache is the one technique that fast motion would stress, so before
shipping, re-validate on a clip with real movement (see below), and if SSIM
dips, drop the cadence from every 3rd frame to every 2nd and re-verify.

## Reproduce it

Prerequisites, once.

- A Gemini Enterprise license on a GCP project (any tier, a trial works).
  AlphaEvolve is not pay-per-call, it is gated by the platform seat.
- A Gemini Enterprise app (engine). List existing ones or create one.

```bash
PROJECT_ID=$(gcloud config get project)
gcloud services enable discoveryengine.googleapis.com

# create an engine (its id is your GE_APP_ID)
curl -X POST \
  "https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/global/collections/default_collection/engines?engineId=my-alphaevolve" \
  -H "Content-Type: application/json" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -d '{"display_name": "my-alphaevolve", "data_store_ids": [], "solution_type": "SOLUTION_TYPE_GENERATIVE_CHAT"}'

# create the assistant inside it (the id must be default_assistant)
curl -X POST \
  "https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/global/collections/default_collection/engines/my-alphaevolve/assistants?assistantId=default_assistant" \
  -H "Content-Type: application/json" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -d '{"display_name": "default_assistant", "web_grounding_type": "WEB_GROUNDING_TYPE_UNSPECIFIED"}'
```

(In this run an existing search-type Gemini Enterprise app also accepted the
experiment, so if you already have an app, try its id first.)

Client and auth.

```bash
git clone https://github.com/Google-Cloud-AI/alphaevolve-on-googlecloud
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python ./alphaevolve-on-googlecloud
gcloud auth application-default login
```

Record the test clip. **It must show a person**, 2 to 3 seconds of yourself
on the webcam (QuickTime, File, New Movie Recording), moving a little so
mask-caching candidates get punished for stale masks. Save it as `clip.mov`
in this folder. It is git-ignored, your face never gets committed.

Smoke test, then evolve.

```bash
.venv/bin/python evaluate.py     # renders goldens, seed must score ssim 1.0

export PROJECT_ID=<your project>
export GE_APP_ID=<your engine id>
.venv/bin/python evolve.py
```

The best program lands in `best_program.swift` (this folder ships the one
from my run). Verify any candidate standalone with
`.venv/bin/python evaluate.py best_program.swift`.

## Re-running on a new clip

The harness is clip-agnostic because the goldens are always regenerated from
the seed on whatever clip is present. To re-run with different footage,

```bash
cp /path/to/new-take.mov clip.mov
rm -rf goldens
.venv/bin/python evaluate.py                     # new goldens + seed check
.venv/bin/python evaluate.py best_program.swift  # re-validate the old winner
.venv/bin/python evolve.py                       # or evolve fresh
```

This is also the honest-validation move. A winner tuned on one clip should be
re-scored on a harder one (more motion) before it ships.

## Files

```
seed.swift           the production blur, wrapped in EVOLVE-BLOCK markers
bench.swift          harness, runs a kernel over the clip, prints JSON metrics
evaluate.py          objective function, compile + run + SSIM gate + speedup
evolve.py            the AlphaEvolve controller loop (client API, not the docs sketch)
best_program.swift   the evolved winner from this run
clip.mov             your test take (git-ignored, bring your own)
goldens/             reference frames + baseline timing (git-ignored, auto-generated)
```

One API note baked into evolve.py, `experiment.list_programs()` returns a
dict wrapper, the programs sit under the `alphaEvolvePrograms` key. The
first version of this script iterated the dict and concluded no candidate
had survived. The programs also remain retrievable server-side after the run,
which is how the winner here was recovered.
