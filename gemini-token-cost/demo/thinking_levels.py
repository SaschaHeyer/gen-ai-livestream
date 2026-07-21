"""Does thinking_level move the bill, and by how much?

Thinking dominates the invoice on short answer work. The 3.6 Flash release
ships a knob for it. This measures the knob rather than trusting the label.

  python thinking_levels.py --repeat 3
  python thinking_levels.py --model gemini-3.5-flash-lite --shape output-heavy
"""
import argparse
import os

from google import genai

PRICES = {
    "gemini-3.6-flash": {"input": 1.50, "output": 7.50},
    "gemini-3.5-flash-lite": {"input": 0.30, "output": 2.50},
}

OUTPUT_HEAVY = (
    "Write a detailed runbook for taking a weekly technical livestream to air. "
    "Cover the rehearsal pass, the scene layout in the streaming software, audio "
    "checks, what to cache as a fallback when a live demo fails, and how to close "
    "the show. Be thorough and use clear sections."
)
INPUT_HEAVY_Q = "In one sentence, name the single biggest risk to the stream."


def measure(client, model, prompt, level):
    cfg = {"generation_config": {"thinking_level": level}} if level else {}
    interaction = client.interactions.create(model=model, input=prompt, **cfg)
    u = interaction.usage
    visible = u.total_output_tokens or 0
    thought = u.total_thought_tokens or 0
    billed = visible + thought
    p = PRICES[model]
    cost = (u.total_input_tokens or 0) / 1e6 * p["input"] + billed / 1e6 * p["output"]
    return {"visible": visible, "thought": thought, "billed": billed, "cost": cost}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemini-3.6-flash", choices=list(PRICES))
    ap.add_argument("--shape", default="input-heavy", choices=["input-heavy", "output-heavy"])
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--levels", nargs="+", default=["default", "low", "high"],
                    help="use the word default for no thinking_level at all")
    args = ap.parse_args()

    levels = [None if lvl == "default" else lvl for lvl in args.levels]

    if args.shape == "output-heavy":
        prompt = OUTPUT_HEAVY
    else:
        with open("fixtures/long-input.txt") as fh:
            prompt = fh.read() + "\n\n" + INPUT_HEAVY_Q

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    print(f"model {args.model}, shape {args.shape}, {args.repeat} sample(s) per level")
    print()
    header = (f"{'thinking_level':<16}{'visible':>9}{'thought':>9}{'billed':>9}"
              f"{'cost USD':>12}{'vs default':>13}")
    print(header)
    print("-" * len(header))

    baseline = None
    for level in levels:
        try:
            rows = [measure(client, args.model, prompt, level) for _ in range(args.repeat)]
        except Exception as exc:
            print(f"{str(level or 'default'):<16} REJECTED, {str(exc)[:150]}")
            continue
        avg = {k: sum(r[k] for r in rows) / len(rows) for k in rows[0]}
        if level is None:
            baseline = avg["cost"]
        delta = ""
        if baseline and level is not None:
            delta = f"{(baseline - avg['cost']) / baseline * 100:+.1f}%"
        print(f"{str(level or 'default'):<16}{avg['visible']:>9.0f}{avg['thought']:>9.0f}"
              f"{avg['billed']:>9.0f}{avg['cost']:>12.6f}{delta:>13}")

    print()
    print("positive percent means cheaper than leaving thinking_level unset")


if __name__ == "__main__":
    main()
