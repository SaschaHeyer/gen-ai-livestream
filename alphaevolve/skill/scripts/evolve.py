#!/usr/bin/env python3
"""Point AlphaEvolve at your own function and evolve a better version.

Generalizes the Google circle_packing example into a utility you run against any
program: mark the region to evolve with EVOLVE-BLOCK markers, define an evaluate()
that returns {metric: score} (higher is better), and this drives the full loop
against your Gemini Enterprise engine, then prints the best program and its score.

    python evolve.py --program examples/circle_packing.py --metric sum_of_radii \
        --inputs '{"n": 26}' --max-programs 20 --out best_program.py

Config comes from the environment (or a .env next to where you run it):
    PROJECT_ID    your Google Cloud project
    GE_APP_ID     your Gemini Enterprise app / engine id
    LOCATION=global  COLLECTION=default_collection  ASSISTANT=default_assistant
    MODEL_1=gemini-3.5-flash  MODEL_2=gemini-3.1-pro-preview  (weighted mixture)

Auth: run `gcloud auth application-default login` once first.
"""
import argparse, asyncio, json, logging, os, importlib.util
from typing import Any, Mapping

import nest_asyncio
from dotenv import load_dotenv

load_dotenv()

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

# A big negative sentinel keeps failed candidates from ever being selected. The
# API requires a numeric score per metric, so this is used instead of -inf.
FAILED_SCORE = -1e12


def make_evaluator(metric: str, inputs: dict):
    """Build the evaluator AlphaEvolve calls on every candidate it generates.

    Your program is exec'd in a fresh namespace, then its evaluate(inputs) is
    called. Whatever it returns under `metric` becomes the candidate's score.
    """

    def evaluate_candidate(program_candidate) -> dict:
        code = program_candidate["content"]["files"][0]["content"]
        score_value = FAILED_SCORE
        insights = []
        try:
            ns = {"np": __import__("numpy"), "Any": Any, "Mapping": Mapping}
            exec(code, ns)
            fn = ns.get("evaluate")
            if callable(fn):
                result = fn(inputs)
                score = result.get(metric)
                if score is not None and score != -float("inf"):
                    score_value = float(score)
                else:
                    insights.append(AlphaEvolveEvaluationInsight(
                        label="Invalid Score",
                        text=f"evaluate() returned no valid '{metric}' (got {score!r}); the candidate broke a constraint."))
            else:
                insights.append(AlphaEvolveEvaluationInsight(
                    label="Invalid Program Structure",
                    text="The program is missing a callable 'evaluate' function."))
        except Exception as e:  # a broken candidate is a signal, not a crash
            insights.append(AlphaEvolveEvaluationInsight(
                label="Runtime Error", text=f"Candidate failed during execution: {e}"))

        scores = AlphaEvolveEvaluationScores(
            scores=[AlphaEvolveEvaluationScore(metric=metric, score=score_value)])
        ev = AlphaEvolveProgramEvaluation(scores=scores, insights=AlphaEvolveEvaluationInsights(
            insights=insights)) if insights else AlphaEvolveProgramEvaluation(scores=scores)
        return ev.model_dump()

    return evaluate_candidate


def main():
    ap = argparse.ArgumentParser(description="Evolve a function with AlphaEvolve.")
    ap.add_argument("--program", required=True, help="Path to your seed program (EVOLVE-BLOCK markers + evaluate()).")
    ap.add_argument("--metric", required=True, help="The score key evaluate() returns, maximized (higher is better).")
    ap.add_argument("--inputs", default="{}", help="JSON dict passed to evaluate(). e.g. '{\"n\": 26}'")
    ap.add_argument("--max-programs", type=int, default=20, help="Search budget (candidates evaluated).")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--out", default="best_program.py", help="Where to write the winning program.")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    seed_code = open(args.program).read()
    if "EVOLVE-BLOCK-START" not in seed_code:
        raise SystemExit("Your program has no # EVOLVE-BLOCK-START / END markers, nothing to evolve.")
    inputs = json.loads(args.inputs)

    client = AlphaEvolveClient(
        project_id=os.environ["PROJECT_ID"],
        location=os.getenv("LOCATION", "global"),
        collection=os.getenv("COLLECTION", "default_collection"),
        engine=os.environ["GE_APP_ID"],
        assistant=os.getenv("ASSISTANT", "default_assistant"),
        base_url=os.getenv("BASE_URL", "discoveryengine.googleapis.com"),
    )
    experiment = AlphaEvolveExperiment(client, make_evaluator(args.metric, inputs), args.max_programs)
    experiment.create_experiment({
        "title": f"Evolve {os.path.basename(args.program)}",
        "problem_description": f"Evolve the marked region to maximize {args.metric}.",
        "program_language": "python",
        "run_settings": {"max_programs": args.max_programs, "concurrency": args.concurrency},
        "generation_settings": {"models": [
            {"name": os.getenv("MODEL_1", "gemini-3.5-flash"), "weight": float(os.getenv("MODEL_1_WEIGHT", "0.7"))},
            {"name": os.getenv("MODEL_2", "gemini-3.1-pro-preview"), "weight": float(os.getenv("MODEL_2_WEIGHT", "0.3"))},
        ]},
    })
    experiment.create_initial_program({
        "content": {"files": [{"path": os.path.basename(args.program), "content": seed_code}]},
        "evaluation": {"scores": {"scores": [{"metric": args.metric, "score": FAILED_SCORE}]}},
    })
    experiment.start_experiment()

    nest_asyncio.apply()
    asyncio.run(run_controller_loop(experiment))

    resp = experiment.list_programs(params={"order_by": f"{args.metric} desc"})
    progs = resp.get("alphaEvolvePrograms", []) if resp else []
    ranked = sorted(((get_score(p, args.metric), p) for p in progs), key=lambda x: x[0], reverse=True)
    ranked = [(s, p) for s, p in ranked if s > FAILED_SCORE / 2]
    if not ranked:
        raise SystemExit("No valid programs produced. Try a larger --max-programs.")
    best_score, best = ranked[0]
    open(args.out, "w").write(best["content"]["files"][0]["content"])
    print(f"\nBest {args.metric} = {best_score:.5f}  (from {len(progs)} candidates)")
    print(f"Winning program written to {args.out}")


if __name__ == "__main__":
    main()
