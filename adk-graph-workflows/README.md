# ADK graph workflows, with a human approval gate

From the Friday livestream, episode 11, 2026-09-18.

An autonomous agent that can issue a refund on its own is a great demo and a poor production
system. This episode builds the other version with Google ADK 2.0, a graph where the routing is
plain Python you can read and test, and where one node suspends the whole run until a human
answers.

Honest framing, ADK 2.0 is not new. Python went GA on 2026-05-19 and the package is on 2.5.0, and
LangGraph reached graph orchestration first. What ADK adds is a Google native option, the same
graph shape across Python and Go, and human in the loop built into the runtime.

Everything runnable lives in [skill/](skill/), see [skill/SKILL.md](skill/SKILL.md).

```bash
pip install -r skill/requirements.txt
export GEMINI_API_KEY=...
python skill/scripts/approval_graph.py "refund my 120 euro plan"
```

Two sharp edges the episode earned, both documented in the skill,

- a human in the loop node must end at its `yield`, code after it runs without waiting
- an unmatched route only logs a warning, use `DEFAULT_ROUTE` as the seatbelt
