# Gemini token cost

What a Gemini prompt actually costs you, including the thinking tokens you never see.

The Interactions API reports thinking separately from output, and Google bills thinking at the
full output rate. Cost off the visible field alone and you can understate the output bill by more
than thirty times on short answer workloads.

## The skill

Everything reusable lives in [skill/](skill/), install that folder.

- [skill/SKILL.md](skill/SKILL.md), the current facts, the sharp edges, and the measured numbers
- [skill/scripts/tokencost.py](skill/scripts/tokencost.py), point it at your own prompt

```bash
export GEMINI_API_KEY=...
pip install -U google-genai
python skill/scripts/tokencost.py "Explain why database indexes slow down writes." --repeat 3
```

## The episode demos

[demo/](demo/) holds the exact scripts run on the stream, kept as the reproduction.

| file | what it shows |
| --- | --- |
| `probe_usage.py` | dumps the whole `usage` object, this is where the thinking field turns up |
| `compare.py` | the A/B comparison across two models and two workload shapes |
| `sampling_check.py` | what the API does when you send the deprecated sampling parameters |
| `sampling_honored.py` | whether `temperature` is actually honoured, it is not |

```bash
pip install -r demo/requirements.txt
python demo/compare.py --shape output-heavy --repeat 3
python demo/compare.py --shape input-heavy --repeat 3
```

## What we measured

2026-07-21, `google-genai==2.12.1`, Python 3.13.3, 3 samples per model,
`gemini-3.5-flash` against `gemini-3.6-flash`.

| workload shape | visible output | thinking | cost |
| --- | --- | --- | --- |
| long answer | 16.3 percent fewer | 5.7 percent fewer | 28.0 percent cheaper |
| long context, short answer | 26.7 percent fewer | 32.3 percent fewer | 36.6 percent cheaper |

Google's claim of 17 percent fewer output tokens reproduced at 16.3 percent on the long answer
shape. The long context shape saved more, not less, even though the input price never moved,
because thinking dominates that bill.

Single runs of the same comparison gave 43.6 and 48.4 percent. Three samples gave 28.0. Sample
size matters more than the model choice here.
