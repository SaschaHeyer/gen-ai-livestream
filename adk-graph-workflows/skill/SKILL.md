---
name: adk-graph-workflows
description: Use this skill when building deterministic agent workflows with Google ADK, routing between nodes with plain Python instead of letting the model decide, or adding a human approval gate that suspends a running agent until a person answers. Covers the ADK 2.0 Workflow graph, edge and route syntax, DEFAULT_ROUTE fallbacks, RequestInput human-in-the-loop, and the two turn suspend and resume protocol. SDKs used, google-adk, google-genai.
---

# ADK Graph Workflows Skill

## Overview

ADK 2.0 lets you declare an agent as a graph. Agents, plain Python functions, and tools are all
nodes, edges decide what runs next, and one node type can suspend the entire run until a human
answers.

- Deterministic routing, the branch is chosen by your code, not by the model
- A human approval gate that genuinely pauses execution
- A default branch so an unexpected label does not end the run quietly

> [!IMPORTANT]
> Use `google-adk>=2.5.0`. ADK Python 2.0 went GA on 2026-05-19 and ADK Go 2.0 on 2026-06-30, and
> the Python package ships a minor roughly every few weeks, 2.5.0 landed 2026-07-16. Pin the
> version, an unpinned graph demo drifts fast.

> [!WARNING]
> Some ADK 2.0 documentation examples show routing via `Event(route=...)` and `Event(message=...)`.
> Neither field exists on `Event` in google-adk 2.5.0, and passing them is silently ignored rather
> than rejected, so the route never fires and the branch just ends. Routing lives on the node
> **Context**, set `ctx.route` and `ctx.output`.

---

## Quick Start

```python
from pydantic import BaseModel
from google.adk import Agent, Context, Workflow
from google.adk.events import RequestInput
from google.adk.workflow import DEFAULT_ROUTE


class Ticket(BaseModel):
    category: str
    amount_eur: float
    summary: str


triage_agent = Agent(
    name="triage_agent",
    model="gemini-flash-latest",
    instruction="Classify the message and extract any amount.",
    output_schema=Ticket,
)


def route_ticket(ctx: Context, node_input: Ticket):
    """The switch. Ordinary Python, so it is readable and unit testable."""
    if node_input.category != "REFUND":
        ctx.route = "NO_MONEY"
    elif node_input.amount_eur <= 50:
        ctx.route = "SMALL"
    else:
        ctx.route = "NEEDS_HUMAN"
    ctx.output = node_input


def ask_for_approval(ctx: Context, node_input: Ticket):
    yield RequestInput(
        message=f"{node_input.amount_eur:.2f} EUR requested. Approve?",
        payload={"amount_eur": node_input.amount_eur},
    )


def settle(ctx: Context, node_input):
    # node_input IS the human's answer, handed straight in.
    decision = (node_input or {}).get("decision", "denied")
    ctx.output = "Approved, proceeding." if decision == "approved" else "Denied, nothing executed."


root_agent = Workflow(
    name="support_desk",
    edges=[
        ("START", triage_agent, route_ticket),
        (route_ticket, {
            "SMALL": auto_approve,
            "NEEDS_HUMAN": ask_for_approval,
            "NO_MONEY": not_money,
            DEFAULT_ROUTE: unroutable,
        }),
        (ask_for_approval, settle),
    ],
)
```

> [!WARNING]
> **A human-in-the-loop node must END at the `yield`.** Any code after the `yield` runs immediately
> in the same pass, without waiting for anyone, and `ctx.resume_inputs` is still `{}` when it does.
> Observable symptom, your node logs its post-approval work during the very first turn and the run
> completes without ever pausing, so an agent cheerfully approves its own action. Put the follow-up
> in the next node instead, where the human's answer arrives as `node_input`.
> Compare `scripts/gotcha_code_after_yield.py` against `scripts/gotcha_ends_at_yield.py` to see both
> behaviours side by side.

> [!WARNING]
> An emitted route with no matching edge does not raise. ADK logs
> `Node 'X' has conditional/DEFAULT edges but none were matched by the emitted route(s): LABEL.
> The branch will end.` and the run finishes with the last node's output still attached, which reads
> like success. Observable symptom, a final output that is your intermediate object rather than a
> handler's result. Always add `DEFAULT_ROUTE` from `google.adk.workflow`, it is a one line seatbelt.

### Resuming a suspended run

The suspend is cooperative. The run emits an event carrying `long_running_tool_ids`, the turn ends,
and you resume by sending a **FunctionResponse** part keyed by that id, plus the original
`invocation_id`.

```python
interrupt_id = invocation_id = None
async for ev in runner.run_async(user_id=USER, session_id=session.id, new_message=msg):
    if ev.long_running_tool_ids:
        interrupt_id = list(ev.long_running_tool_ids)[0]
        invocation_id = ev.invocation_id

resume = types.Part(function_response=types.FunctionResponse(
    id=interrupt_id, name="ask_for_approval", response={"decision": "approved"}))

async for ev in runner.run_async(
    user_id=USER, session_id=session.id,
    new_message=types.Content(role="user", parts=[resume]),
    invocation_id=invocation_id,
):
    ...
```

> [!WARNING]
> The resume message may not mix a FunctionResponse part with a text part. ADK raises
> `Message cannot contain both function responses and text`, because function responses resume an
> existing invocation while text starts a new one.

> [!IMPORTANT]
> Node behaviour on resume is controlled by `rerun_on_resume`. It defaults to `False` on a node,
> meaning the node completes immediately using the human's answer as its output, which is why the
> answer shows up as the next node's `node_input`. Set it to `True` only if you want the node body
> to run again from scratch.

## Workflow

1. Read the user's request and identify which step must not be taken autonomously, typically
   anything moving money, deleting data, or contacting a customer.
2. Put the model only where genuine ambiguity lives, usually a single classification or extraction
   node with an `output_schema`. Everything downstream is plain Python.
3. Run `scripts/approval_graph.py` with the user's own message and threshold to see the shape
   working before adapting it, for example
   `python scripts/approval_graph.py "refund my 120 euro plan" --limit 50`.
4. Report which branch fired and whether the run suspended, and hand back the resulting graph code.

## Dependencies and Prerequisites

- `google-adk >= 2.5.0` (verified on 2.5.0)
- Python `>= 3.10`, the package floor. Verified on 3.12.
- `GEMINI_API_KEY` in the environment for any node that is an `Agent`.

```bash
pip install "google-adk==2.5.0"
```

## Supporting files

- [scripts/approval_graph.py](scripts/approval_graph.py), the parameterized graph. Point it at your
  own message and limit, `python scripts/approval_graph.py "refund my 35 euro deposit" --limit 20`.
  Add `--answer approved` or `--answer denied` to skip the interactive prompt in CI.
- [scripts/gotcha_ends_at_yield.py](scripts/gotcha_ends_at_yield.py), the correct HITL shape, the run
  suspends and the downstream node waits. `python scripts/gotcha_ends_at_yield.py`
- [scripts/gotcha_code_after_yield.py](scripts/gotcha_code_after_yield.py), the same graph with code
  after the `yield`, which does not suspend. `python scripts/gotcha_code_after_yield.py`
- [requirements.txt](requirements.txt), the pinned version floor.

Both gotcha scripts run without an API key, they use plain function nodes only.
