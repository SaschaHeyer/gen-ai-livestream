#!/usr/bin/env python3
"""Measure what a prompt actually costs across Gemini models.

Counts BILLED output tokens, which is visible output plus thinking tokens,
because Google bills thinking at the output rate and the thinking is usually
bigger than the answer.

Examples
  python tokencost.py "Summarise the risks in this plan"
  python tokencost.py --file prompt.txt --repeat 5
  python tokencost.py --file prompt.txt --models gemini-3.6-flash gemini-3.5-flash-lite
"""
import argparse
import os
import sys

from google import genai

# Published prices, USD per 1M tokens, standard paid tier.
# Source, https://ai.google.dev/gemini-api/docs/pricing
# Verified 2026-07-21. Update this table when Google moves prices.
PRICES = {
    "gemini-3.6-flash": {"input": 1.50, "output": 7.50},
    "gemini-3.5-flash": {"input": 1.50, "output": 9.00},
    "gemini-3.5-flash-lite": {"input": 0.30, "output": 2.50},
}


def measure(client, model, prompt):
    interaction = client.interactions.create(model=model, input=prompt)
    u = interaction.usage
    visible = u.total_output_tokens or 0
    thought = u.total_thought_tokens or 0
    billed_output = visible + thought
    price = PRICES[model]
    cost = (
        (u.total_input_tokens or 0) / 1e6 * price["input"]
        + billed_output / 1e6 * price["output"]
    )
    return {
        "input": u.total_input_tokens or 0,
        "visible": visible,
        "thought": thought,
        "billed_output": billed_output,
        "cost": cost,
    }


def mean(rows, key):
    return sum(r[key] for r in rows) / len(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt", nargs="?", help="the prompt text, or use --file")
    ap.add_argument("--file", help="read the prompt from a file instead")
    ap.add_argument("--models", nargs="+", default=["gemini-3.5-flash", "gemini-3.6-flash"],
                    help=f"models to compare, known, {', '.join(PRICES)}")
    ap.add_argument("--repeat", type=int, default=3,
                    help="samples per model, default 3, thinking token counts vary a lot")
    ap.add_argument("--monthly-calls", type=int,
                    help="also project a monthly bill at this call volume")
    args = ap.parse_args()

    if args.file:
        with open(args.file) as fh:
            prompt = fh.read()
    elif args.prompt:
        prompt = args.prompt
    else:
        ap.error("give a prompt as an argument or use --file")

    unknown = [m for m in args.models if m not in PRICES]
    if unknown:
        ap.error(f"no price on file for {', '.join(unknown)}, add it to PRICES first")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("set GEMINI_API_KEY first")
    client = genai.Client(api_key=api_key)

    print(f"prompt, {len(prompt)} characters, {args.repeat} sample(s) per model")
    print()
    header = (f"{'model':<24}{'in':>8}{'visible':>10}{'thought':>10}"
              f"{'billed out':>12}{'cost USD':>12}")
    print(header)
    print("-" * len(header))

    summary = []
    for model in args.models:
        rows = [measure(client, model, prompt) for _ in range(args.repeat)]
        for r in rows:
            print(f"{model:<24}{r['input']:>8}{r['visible']:>10}{r['thought']:>10}"
                  f"{r['billed_output']:>12}{r['cost']:>12.6f}")
        avg = {k: mean(rows, k) for k in ("input", "visible", "thought", "billed_output", "cost")}
        avg["model"] = model
        summary.append(avg)
        if args.repeat > 1:
            print(f"{'  mean':<24}{avg['input']:>8.0f}{avg['visible']:>10.0f}"
                  f"{avg['thought']:>10.0f}{avg['billed_output']:>12.0f}{avg['cost']:>12.6f}")
            lo = min(r["cost"] for r in rows)
            hi = max(r["cost"] for r in rows)
            print(f"{'  cost range':<24}{lo:.6f} to {hi:.6f}")
        print()

    for s in summary:
        share = (s["thought"] / s["billed_output"] * 100) if s["billed_output"] else 0
        print(f"{s['model']}, thinking is {share:.0f} percent of billed output")
    print()

    cheapest = min(summary, key=lambda s: s["cost"])
    print(f"cheapest, {cheapest['model']} at {cheapest['cost']:.6f} USD per call")
    for s in summary:
        if s["model"] != cheapest["model"] and s["cost"]:
            delta = (s["cost"] - cheapest["cost"]) / s["cost"] * 100
            print(f"  {delta:.1f} percent cheaper than {s['model']}")

    if args.monthly_calls:
        print()
        print(f"projected at {args.monthly_calls:,} calls per month")
        for s in summary:
            print(f"  {s['model']:<24}{s['cost'] * args.monthly_calls:>12.2f} USD")

    if args.repeat == 1:
        print()
        print("one sample per model, treat this as an anecdote, rerun with --repeat 3")


if __name__ == "__main__":
    main()
