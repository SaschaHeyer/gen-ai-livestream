#!/usr/bin/env python3
"""blurlab AlphaEvolve runner. Evolves the camera background blur kernel
(seed.swift) against the local evaluator (evaluate.py).

Setup, once.

    uv venv --python 3.12 .venv
    uv pip install --python .venv/bin/python <path to alphaevolve-on-googlecloud clone>
    gcloud auth application-default login

Run.

    export PROJECT_ID=<your gcp project>
    export GE_APP_ID=<your engine id>
    .venv/bin/python evolve.py

Optional env vars, MAX_PROGRAMS (default 40), CONCURRENCY (default 2,
keep it low, candidates share one GPU and parallel runs skew the
timing), MODEL_1 / MODEL_2 and MODEL_1_WEIGHT / MODEL_2_WEIGHT.

The best program lands in best_program.swift. Confirm it with
evaluate.py, then port the evolve block into SceneCompositor.blurredCamera.
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

from evaluate import FAILED_SCORE, SEED, ensure_goldens, evaluate

PRIMARY_METRIC = "speedup"

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


def evaluation_fn(program_candidate) -> dict:
    """Adapter between the AlphaEvolve candidate shape and evaluate.py."""
    insights = []
    scores = {"speedup": FAILED_SCORE, "ssim": 0.0}
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

    if scores["speedup"] == FAILED_SCORE and not insights:
        if scores.get("ssim", 0) > 0:
            insights.append(AlphaEvolveEvaluationInsight(
                label="SSIM Gate Failed",
                text=f"Output differs visibly from the reference (ssim {scores['ssim']}). "
                     "The kernel must produce the same image, only faster."))
        else:
            insights.append(AlphaEvolveEvaluationInsight(
                label="Compile Or Run Failed",
                text="The candidate did not compile with swiftc or crashed while "
                     "rendering. Check the required class name and signature."))

    print(f"  candidate scored {scores}", flush=True)
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

    # Render goldens and sanity-check the seed before burning candidates.
    ensure_goldens()
    seed_code = SEED.read_text()
    baseline = evaluate(seed_code)
    print(f"seed scores {baseline}")
    if baseline["speedup"] < 0:
        sys.exit("the seed fails its own gate, fix the harness before evolving")

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
        "title": "Stage Studio camera background blur",
        "problem_description": PROBLEM,
        "program_language": "swift",
        "run_settings": {"max_programs": max_programs, "concurrency": concurrency},
        "generation_settings": {"models": models},
    })
    experiment.create_initial_program({
        "content": {"files": [{"path": "candidate.swift", "content": seed_code}]},
        "evaluation": {"scores": {"scores": [
            {"metric": PRIMARY_METRIC, "score": baseline["speedup"]},
            {"metric": "ssim", "score": baseline["ssim"]},
        ]}},
    })
    experiment.start_experiment()
    asyncio.run(run_controller_loop(experiment))

    # Pull the highest-scoring program and save it for review.
    try:
        # list_programs returns a dict wrapper, the programs sit under the
        # alphaEvolvePrograms key.
        programs = (experiment.list_programs() or {}).get("alphaEvolvePrograms", [])
        scored = [(get_score(p, PRIMARY_METRIC), p) for p in programs]
        scored = [(s, p) for s, p in scored if s is not None and s > 0]
        if scored:
            best_score, best = max(scored, key=lambda item: item[0])
            code = best["content"]["files"][0]["content"]
            out = Path(__file__).resolve().parent / "best_program.swift"
            out.write_text(code)
            print(f"best speedup {best_score}, program written to {out}")
        else:
            print("no candidate beat the gate, nothing written")
    except Exception as error:
        print(f"could not fetch the best program automatically ({error}), "
              "use experiment.list_programs() in a notebook to inspect the run")


if __name__ == "__main__":
    main()
