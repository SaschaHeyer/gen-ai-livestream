"""Prove the real two-turn suspend and resume, no LLM."""
import asyncio
from google.adk import Workflow, Context
from google.adk.workflow import DEFAULT_ROUTE
from google.adk.events import RequestInput
from google.adk.runners import InMemoryRunner
from google.genai import types

CALLS = []


def triage(ctx: Context, node_input=None):
    ctx.route = "BIG"
    ctx.output = 120


def approval(ctx: Context, node_input=None):
    CALLS.append(dict(ctx.resume_inputs) if ctx.resume_inputs else {})
    print(f"[approval] body entered, resume_inputs={ctx.resume_inputs}")
    answer = yield RequestInput(message="Approve 120 EUR refund?")
    print(f"[approval] after yield, yielded value={answer!r} resume_inputs={ctx.resume_inputs}")
    ctx.output = f"decided: {ctx.resume_inputs}"


def fallback(ctx: Context, node_input=None):
    ctx.output = "fallback"


root_agent = Workflow(
    name="smoke2",
    edges=[("START", triage), (triage, {"BIG": approval, DEFAULT_ROUTE: fallback})],
)


async def main():
    runner = InMemoryRunner(agent=root_agent, app_name="smoke2")
    s = await runner.session_service.create_session(app_name="smoke2", user_id="sascha")

    print("--- TURN 1 ---")
    interrupt_id = None
    invocation_id = None
    async for ev in runner.run_async(
        user_id="sascha", session_id=s.id,
        new_message=types.Content(role="user", parts=[types.Part(text="refund")]),
    ):
        print(f"  ev output={ev.output!r} lrt={ev.long_running_tool_ids} inv={ev.invocation_id}")
        if ev.long_running_tool_ids:
            interrupt_id = list(ev.long_running_tool_ids)[0]
            invocation_id = ev.invocation_id
    print("interrupt_id:", interrupt_id, "invocation_id:", invocation_id)

    print("--- TURN 2, resume with approval ---")
    fr = types.Part(function_response=types.FunctionResponse(
        id=interrupt_id, name="approval", response={"decision": "approved"}))
    async for ev in runner.run_async(
        user_id="sascha", session_id=s.id,
        new_message=types.Content(role="user", parts=[fr]),
        invocation_id=invocation_id,
    ):
        print(f"  ev output={ev.output!r} lrt={ev.long_running_tool_ids}")

    print("\napproval body entered", len(CALLS), "times, resume_inputs each time:", CALLS)


asyncio.run(main())
