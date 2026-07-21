"""What actually happens when you still send the deprecated sampling parameters.

The July 21 changelog deprecates temperature, top_p and top_k and does not say
what replaces them or whether existing code keeps working. So we ask the API.
"""
import os
import warnings
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
PROMPT = "In one sentence, what makes a livestream demo trustworthy?"


def attempt(label, **kwargs):
    print(f"--- {label}")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            interaction = client.interactions.create(
                model="gemini-3.6-flash", input=PROMPT, **kwargs
            )
            print("  result, accepted")
            print(f"  output tokens, {interaction.usage.total_output_tokens}")
        except Exception as exc:
            print(f"  result, raised {type(exc).__name__}")
            print(f"  message, {str(exc)[:400]}")
        for w in caught:
            print(f"  warning, {w.category.__name__}, {w.message}")
    print()


attempt("baseline, no sampling parameters")
attempt("temperature=0.2 as a top level argument", temperature=0.2)
attempt("temperature inside generation_config", generation_config={"temperature": 0.2})
attempt("top_p=0.8 as a top level argument", top_p=0.8)
attempt("top_k=40 as a top level argument", top_k=40)
