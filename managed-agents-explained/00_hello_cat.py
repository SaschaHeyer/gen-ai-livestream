"""Managed Agents, hello world. The fun version.

One API call. No container, no sandbox, no infrastructure.

We do not describe the cat. The agent invents it, writes the program that
draws it, runs that program in a Linux machine Google provisioned, and reads
its own stdout back to us.

    export GEMINI_API_KEY=...
    pip install -U google-genai
    python demo/hello_cat.py
"""
import os
import time

from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

TASK = """Write cat.py, a program that draws an ASCII-art cat with HELLO FUSION
in a speech bubble above it.

Everything else about the cat is your call. Give it a personality, an outfit, an
accessory, a mood, whatever amuses you. Surprise me.

Make cat.py use Python's random module to pick between several variants that you
invent, so no two runs of the file produce the same cat.

Then run it and report the exact output verbatim."""

t0 = time.time()

interaction = client.interactions.create(
    agent="antigravity-preview-05-2026",          # the base agent, nothing to create first
    input=TASK,
    environment={"type": "remote"},                # "remote" = Google runs the Linux box
)

# The answer.
print(interaction.output_text)

# The part a chat completion does not give you: every step it actually took.
print("\n--- what it did in the sandbox ---")
for step in interaction.steps or []:
    if step.type == "function_call":
        print(f"  [call]   {step.name}")
    elif step.type == "function_result":
        print(f"  [result] {step.name}")
    elif step.type == "code_execution_call":
        print("  [code]   ran code in the sandbox")
    elif step.type == "code_execution_result":
        print("  [stdout] real output, real exit code")

# Where the tokens actually went. A managed agent is a loop, not one call:
# every turn re-reads the whole prefix, so input is counted again each time.
u = interaction.usage
print(f"\nstatus: {interaction.status}   {time.time() - t0:.1f}s")
print(f"  total    {u.total_tokens:>8,}")
print(f"  input    {u.total_input_tokens:>8,}   (re-read on every turn)")
print(f"  cached   {getattr(u, 'total_cached_tokens', 0) or 0:>8,}   (billed at about a tenth)")
print(f"  thinking {getattr(u, 'total_thought_tokens', 0) or 0:>8,}")
print(f"  output   {u.total_output_tokens:>8,}   (the part you actually read)")
