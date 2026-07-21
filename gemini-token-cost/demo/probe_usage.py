"""Probe what the usage object actually looks like, so the meter reads the right field."""
import os
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

interaction = client.interactions.create(
    model="gemini-3.6-flash",
    input="Name three things worth checking before a livestream goes live.",
)

usage = interaction.usage
print("type:", type(usage).__name__)
print()
print("--- all non-private attributes ---")
for name in dir(usage):
    if name.startswith("_"):
        continue
    value = getattr(usage, name)
    if callable(value):
        continue
    print(f"{name} = {value!r}")

print()
print("--- model_dump ---")
try:
    print(usage.model_dump())
except Exception as exc:
    print("no model_dump:", exc)
