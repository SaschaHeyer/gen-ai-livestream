"""Is temperature inside generation_config actually honored, or silently swallowed?

Accepted is not the same as honored. Two probes.
  1. Send an out of range value. If the API validates it, it is parsing the field.
  2. Send temperature 0 repeatedly. If it is honored, greedy decoding should make
     the answers identical. If they vary, the field is being ignored.
"""
import os
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
PROMPT = (
    "Name one German city worth visiting. Answer with the city name only, nothing else."
)
N = 5


def ask(**cfg):
    interaction = client.interactions.create(
        model="gemini-3.6-flash", input=PROMPT, **cfg
    )
    return (interaction.output_text or "").strip()


print("--- probe 1, out of range temperature 999, does the API validate the field")
try:
    print("  answer:", ask(generation_config={"temperature": 999}))
    print("  result, NOT rejected, so the field is likely ignored")
except Exception as exc:
    print(f"  result, rejected, {type(exc).__name__}")
    print(f"  message, {str(exc)[:300]}")
    print("  reading, the API parsed and validated the field, so it is not ignored")

print()
for label, cfg in (
    ("probe 2, temperature 0.0", {"generation_config": {"temperature": 0.0}}),
    ("probe 3, temperature 2.0", {"generation_config": {"temperature": 2.0}}),
    ("probe 4, no config at all", {}),
):
    answers = [ask(**cfg) for _ in range(N)]
    print(f"--- {label}, {N} times")
    for a in answers:
        print("  ", a)
    print(f"  distinct answers, {len(set(answers))} of {N}")
    print()

print("reading, if temperature 0.0 is far more consistent than temperature 2.0,")
print("the parameter is still being honored despite the deprecation notice")
