#!/usr/bin/env python3
"""encoderlab AlphaEvolve runner. Evolves Stage Studio's ffmpeg encoder
arguments (seed.py) against the local VMAF evaluator (evaluate.py).

Uses the alpha_evolve client from the blurlab venv, run it as

    export PROJECT_ID=<gcp project with a Gemini Enterprise license>
    export GE_APP_ID=<engine id>
    ../blurlab/.venv/bin/python evolve.py

Optional env vars, MAX_PROGRAMS (default 40), CONCURRENCY (default 2),
MODEL_1 / MODEL_2 and MODEL_1_WEIGHT / MODEL_2_WEIGHT.

The best program lands in best_program.py. Confirm it standalone with
evaluate.py, then port the winning arguments into the ffmpeg command in
Sources/Stream/FFmpegStreamer.swift.
"""

import asyncio
import os
import sys
from pathlib import Path

from alpha_evolve.client import AlphaEvolveClient
from alpha_evolve.controller import run_controller_loop
from alpha_evolve.experiment import AlphaEvolveExperiment
from alpha_evolve.models import (
    AlphaEvolveEvaluationInsight,
    AlphaEvolveEvaluationInsights,
    AlphaEvolveEvaluationScore,
    AlphaEvolveEvaluationScores,
    AlphaEvolveProgramEvaluation,
)
from alpha_evolve.visualization import get_score

from evaluate import FAILED_SCORE, TARGET_KBPS, evaluate

LAB = Path(__file__).resolve().parent
SEED = LAB / "seed.py"
PRIMARY_METRIC = "vmaf"

PROBLEM = f"""\
Maximize the perceptual video quality (VMAF, 0 to 100, higher is better) of
a live-streaming H.264 encode at a fixed bandwidth budget. The encoder runs
inside a macOS streaming app on Apple silicon and pushes RTMPS to YouTube
and LinkedIn.

The candidate is a Python function encoder_args() returning a flat list of
ffmpeg output arguments. The evaluator encodes a fixed 1440p30 program-feed
clip (mixed screen share and camera content) with those arguments and
scores VMAF against the source.

Hard gates, violating any returns a failure score. The encoder must remain
h264_videotoolbox (hardware encode on the media engine is a product
requirement, do not switch to libx264 or any software or non-h264 encoder).
Measured output bitrate at most {TARGET_KBPS} kbps plus 5 percent.
Keyframe gap at most 2.1 seconds. Encode speed at least realtime.

Important context. The current settings measure only about 1500 kbps on
this content, far below the {TARGET_KBPS} kbps budget, because the rate
control undershoots on partly static screen content. Spending more of the
allowed budget on quality is legitimate and encouraged, as long as the
measured bitrate stays under the cap.

Ideas worth exploring. h264_videotoolbox private options (see ffmpeg -h
encoder=h264_videotoolbox), for example constant_bit_rate, prio_speed,
power_efficient, entropy coder selection, profile and level. Rate control
shaping via -b:v, -maxrate and -bufsize combinations that use more of the
budget. Keyframe interval up to the 2.1s cap. Quality-biased flags that
still hold realtime speed, the seed encodes at 3.6x realtime so there is
speed headroom to trade.
"""


def evaluation_fn(program_candidate) -> dict:
    insights = []
    scores = {"vmaf": FAILED_SCORE}
    try:
        files = program_candidate.get("content", {}).get("files", [])
        if files:
            scores = evaluate(files[0]["content"])
        else:
            insights.append(AlphaEvolveEvaluationInsight(
                label="Invalid Program Structure",
                text="The candidate contains no files."))
    except Exception as error:
        insights.append(AlphaEvolveEvaluationInsight(
            label="Evaluator Error", text=str(error)))

    reason = scores.pop("reason", None)
    if reason:
        insights.append(AlphaEvolveEvaluationInsight(
            label="Gate Failed", text=reason))

    print(f"  candidate scored {scores}" + (f" ({reason})" if reason else ""),
          flush=True)
    score_list = AlphaEvolveEvaluationScores(scores=[
        AlphaEvolveEvaluationScore(metric=metric, score=float(value))
        for metric, value in scores.items()
    ])
    if insights:
        evaluation = AlphaEvolveProgramEvaluation(
            scores=score_list,
            insights=AlphaEvolveEvaluationInsights(insights=insights))
    else:
        evaluation = AlphaEvolveProgramEvaluation(scores=score_list)
    return evaluation.model_dump()


def main():
    project = os.environ.get("PROJECT_ID")
    engine = os.environ.get("GE_APP_ID")
    if not project or not engine:
        sys.exit("set PROJECT_ID and GE_APP_ID")

    max_programs = int(os.environ.get("MAX_PROGRAMS", "40"))
    concurrency = int(os.environ.get("CONCURRENCY", "2"))
    models_raw = [
        (os.environ.get("MODEL_1", "gemini-3.5-flash"),
         float(os.environ.get("MODEL_1_WEIGHT", "0.7"))),
        (os.environ.get("MODEL_2", "gemini-3.1-pro-preview"),
         float(os.environ.get("MODEL_2_WEIGHT", "0.3"))),
    ]
    models = [{"name": name, "weight": weight} for name, weight in models_raw if name]

    seed_code = SEED.read_text()
    baseline = evaluate(seed_code)
    print(f"seed scores {baseline}")
    if baseline["vmaf"] < 0:
        sys.exit("the seed fails its own gates, fix the harness before evolving")

    client = AlphaEvolveClient(
        project_id=project,
        location=os.environ.get("LOCATION", "global"),
        collection=os.environ.get("COLLECTION", "default_collection"),
        engine=engine,
        assistant=os.environ.get("ASSISTANT", "default_assistant"),
        base_url=os.environ.get("BASE_URL", "discoveryengine.googleapis.com"),
    )
    experiment = AlphaEvolveExperiment(client, evaluation_fn, max_programs)
    experiment.create_experiment({
        "title": "Stage Studio encoder quality at fixed bitrate",
        "problem_description": PROBLEM,
        "program_language": "python",
        "run_settings": {"max_programs": max_programs, "concurrency": concurrency},
        "generation_settings": {"models": models},
    })
    experiment.create_initial_program({
        "content": {"files": [{"path": "candidate.py", "content": seed_code}]},
        "evaluation": {"scores": {"scores": [
            {"metric": metric, "score": float(value)}
            for metric, value in baseline.items()
        ]}},
    })
    experiment.start_experiment()
    asyncio.run(run_controller_loop(experiment))

    try:
        programs = (experiment.list_programs() or {}).get("alphaEvolvePrograms", [])
        scored = [(get_score(p, PRIMARY_METRIC), p) for p in programs]
        scored = [(s, p) for s, p in scored if s is not None and s > 0]
        if scored:
            best_score, best = max(scored, key=lambda item: item[0])
            code = best["content"]["files"][0]["content"]
            out = LAB / "best_program.py"
            out.write_text(code)
            print(f"best vmaf {best_score} (baseline {baseline['vmaf']}), "
                  f"program written to {out}")
        else:
            print("no candidate beat the gates, nothing written")
    except Exception as error:
        print(f"could not fetch the best program automatically ({error})")


if __name__ == "__main__":
    main()
