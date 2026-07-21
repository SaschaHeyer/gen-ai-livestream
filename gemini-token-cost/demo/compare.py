"""Compare what the same task actually costs on two Gemini models.

Reads real token counts off the usage object and multiplies by the published
per-million prices. The point of the script is that the billed output is
output tokens PLUS thought tokens, not the output tokens alone.
"""
import argparse
import os
from google import genai

# Published prices, USD per 1M tokens, standard paid tier.
# Source, https://ai.google.dev/gemini-api/docs/pricing
PRICES = {
    "gemini-3.5-flash": {"input": 1.50, "output": 9.00},
    "gemini-3.6-flash": {"input": 1.50, "output": 7.50},
    "gemini-3.5-flash-lite": {"input": 0.30, "output": 2.50},
}

OUTPUT_HEAVY = (
    "Write a detailed runbook for taking a weekly technical livestream to air. "
    "Cover the rehearsal pass, the scene layout in the streaming software, audio "
    "checks, what to cache as a fallback when a live demo fails, and how to close "
    "the show. Be thorough and use clear sections."
)

INPUT_HEAVY_QUESTION = (
    "Read the notes above. In one sentence, name the single biggest risk to the stream."
)


def measure(client, model, prompt):
    interaction = client.interactions.create(model=model, input=prompt)
    u = interaction.usage
    thought = u.total_thought_tokens or 0
    visible = u.total_output_tokens or 0
    billed_output = visible + thought
    p = PRICES[model]
    cost = (u.total_input_tokens / 1e6) * p["input"] + (billed_output / 1e6) * p["output"]
    return {
        "model": model,
        "input": u.total_input_tokens,
        "visible_output": visible,
        "thought": thought,
        "billed_output": billed_output,
        "total_tokens": u.total_tokens,
        "cost": cost,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shape", choices=["output-heavy", "input-heavy"], default="output-heavy")
    ap.add_argument("--models", nargs="+", default=["gemini-3.5-flash", "gemini-3.6-flash"])
    ap.add_argument("--repeat", type=int, default=1,
                    help="samples per model, thinking tokens vary a lot so 1 is an anecdote")
    args = ap.parse_args()

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    if args.shape == "output-heavy":
        prompt = OUTPUT_HEAVY
    else:
        with open("fixtures/long-input.txt") as fh:
            prompt = fh.read() + "\n\n" + INPUT_HEAVY_QUESTION

    print(f"shape, {args.shape}, {args.repeat} sample(s) per model")
    print()
    header = f"{'model':<24}{'in':>8}{'visible':>10}{'thought':>10}{'billed out':>12}{'cost USD':>12}"
    print(header)
    print("-" * len(header))

    means = []
    for model in args.models:
        samples = [measure(client, model, prompt) for _ in range(args.repeat)]
        for r in samples:
            print(
                f"{r['model']:<24}{r['input']:>8}{r['visible_output']:>10}"
                f"{r['thought']:>10}{r['billed_output']:>12}{r['cost']:>12.6f}"
            )
        mean = {k: sum(s[k] for s in samples) / len(samples)
                for k in ("input", "visible_output", "thought", "billed_output", "cost")}
        mean["model"] = model
        mean["cost_min"] = min(s["cost"] for s in samples)
        mean["cost_max"] = max(s["cost"] for s in samples)
        means.append(mean)
        if args.repeat > 1:
            print(
                f"{'  mean':<24}{mean['input']:>8.0f}{mean['visible_output']:>10.0f}"
                f"{mean['thought']:>10.0f}{mean['billed_output']:>12.0f}{mean['cost']:>12.6f}"
            )
            print(f"{'  cost range':<24}{mean['cost_min']:.6f} to {mean['cost_max']:.6f}")
        print()

    if len(means) == 2:
        a, b = means
        for label, key in (("visible output tokens", "visible_output"),
                           ("thinking tokens", "thought"),
                           ("billed output tokens", "billed_output")):
            if a[key]:
                print(f"{label}, {b['model']} vs {a['model']}, {(a[key] - b[key]) / a[key] * 100:+.1f} percent")
        if a["cost"]:
            print(f"cost, {b['model']} vs {a['model']}, {(a['cost'] - b['cost']) / a['cost'] * 100:+.1f} percent")
        print()
        print("positive percent means the newer model used less or cost less")
        if args.repeat == 1:
            print("one sample per model, treat this as an anecdote, rerun with --repeat 3")


if __name__ == "__main__":
    main()
