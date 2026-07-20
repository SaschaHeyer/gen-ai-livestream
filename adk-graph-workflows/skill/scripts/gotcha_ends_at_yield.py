"""HITL node that ENDS at the yield, with a downstream node that must wait."""
import asyncio
from google.adk import Workflow, Context
from google.adk.workflow import DEFAULT_ROUTE
from google.adk.events import RequestInput
from google.adk.runners import InMemoryRunner
from google.genai import types

SEEN = []


def triage(ctx: Context, node_input=None):
    ctx.route = "BIG"
    ctx.output = 120


def approval(ctx: Context, node_input=None):
    SEEN.append("approval-entered")
    yield RequestInput(message="Approve 120 EUR refund? Reply approved or denied.")


def settle(ctx: Context, node_input=None):
    SEEN.append(f"settle-ran node_input={node_input!r}")
    print(f"[settle] node_input={node_input!r}")
    ctx.output = f"settled with {node_input!r}"


def fallback(ctx: Context, node_input=None):
    ctx.output = "fallback"


root_agent = Workflow(
    name="smoke3",
    edges=[
        ("START", triage),
        (triage, {"BIG": (approval,), DEFAULT_ROUTE: fallback}),
        (approval, settle),
    ],
)


async def main():
    runner = InMemoryRunner(agent=root_agent, app_name="smoke3")
    s = await runner.session_service.create_session(app_name="smoke3", user_id="sascha")

    print("--- TURN 1 ---")
    iid = inv = None
    async for ev in runner.run_async(
        user_id="sascha", session_id=s.id,
        new_message=types.Content(role="user", parts=[types.Part(text="refund")]),
    ):
        print(f"  ev out={ev.output!r} lrt={ev.long_running_tool_ids}")
        if ev.long_running_tool_ids:
            iid, inv = list(ev.long_running_tool_ids)[0], ev.invocation_id
    print("SEEN after turn 1:", SEEN)
    print("interrupt:", iid)

    print("--- TURN 2, resume approved ---")
    fr = types.Part(function_response=types.FunctionResponse(
        id=iid, name="approval", response={"decision": "approved"}))
    async for ev in runner.run_async(
        user_id="sascha", session_id=s.id,
        new_message=types.Content(role="user", parts=[fr]),
        invocation_id=inv,
    ):
        print(f"  ev out={ev.output!r} lrt={ev.long_running_tool_ids}")
    print("SEEN after turn 2:", SEEN)


asyncio.run(main())
