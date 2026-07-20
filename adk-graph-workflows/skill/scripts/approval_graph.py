"""Run an ADK graph workflow with a human approval gate, on your own inputs.

Point it at your own message and your own auto-approve limit.

  python approval_graph.py "refund my 120 euro plan"
  python approval_graph.py "refund my 9 euro pack" --limit 20
  python approval_graph.py "refund my 120 euro plan" --answer denied
  python approval_graph.py "..." --model gemini-flash-latest

Needs GEMINI_API_KEY in the environment and google-adk>=2.5.0.

Verified against google-adk==2.5.0, Python 3.12, on 2026-07-20.
"""

import argparse
import asyncio

from pydantic import BaseModel

from google.adk import Agent, Context, Workflow
from google.adk.events import RequestInput
from google.adk.runners import InMemoryRunner
from google.adk.workflow import DEFAULT_ROUTE
from google.genai import types

APP = "approval_graph"
USER = "local"


class Ticket(BaseModel):
    category: str  # REFUND, BUG, or QUESTION
    amount_eur: float
    summary: str


def build(model: str, limit: float) -> Workflow:
    triage_agent = Agent(
        name="triage_agent",
        model=model,
        instruction="""Read the customer message and fill the fields.

category is REFUND if they want money back, BUG if something is broken with no
money involved, otherwise QUESTION.
amount_eur is the amount they are asking for, or 0 when they name no amount.
summary is one short sentence in plain English.""",
        output_schema=Ticket,
    )

    def route_ticket(ctx: Context, node_input: Ticket):
        if node_input.category != "REFUND":
            ctx.route = "NO_MONEY"
        elif node_input.amount_eur <= limit:
            ctx.route = "SMALL"
        else:
            ctx.route = "NEEDS_HUMAN"
        ctx.output = node_input
        print(f"  [router] {node_input.category} {node_input.amount_eur:.2f} EUR -> {ctx.route}")

    def auto_approve(ctx: Context, node_input: Ticket):
        ctx.output = f"Auto approved {node_input.amount_eur:.2f} EUR, at or under the {limit:.0f} EUR limit."

    def ask_for_approval(ctx: Context, node_input: Ticket):
        # This function MUST end at the yield. See the SKILL.md warning.
        yield RequestInput(
            message=f"{node_input.amount_eur:.2f} EUR requested. {node_input.summary}\nApprove?",
            payload={"amount_eur": node_input.amount_eur, "summary": node_input.summary},
        )

    def settle(ctx: Context, node_input):
        decision = (node_input or {}).get("decision", "denied")
        ctx.output = (
            "Approved by a human, proceeding."
            if decision == "approved"
            else "Denied by a human, nothing was executed."
        )

    def not_money(ctx: Context, node_input: Ticket):
        ctx.output = f"No money involved, filed as {node_input.category}. {node_input.summary}"

    def unroutable(ctx: Context, node_input=None):
        ctx.output = "Could not route this one, escalating to a human queue."

    return Workflow(
        name=APP,
        edges=[
            ("START", triage_agent, route_ticket),
            (
                route_ticket,
                {
                    "SMALL": auto_approve,
                    "NEEDS_HUMAN": ask_for_approval,
                    "NO_MONEY": not_money,
                    DEFAULT_ROUTE: unroutable,
                },
            ),
            (ask_for_approval, settle),
        ],
    )


async def run(message: str, model: str, limit: float, canned: str | None):
    runner = InMemoryRunner(agent=build(model, limit), app_name=APP)
    session = await runner.session_service.create_session(app_name=APP, user_id=USER)

    interrupt_id = invocation_id = final = None
    async for ev in runner.run_async(
        user_id=USER,
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=message)]),
    ):
        if ev.long_running_tool_ids:
            interrupt_id = list(ev.long_running_tool_ids)[0]
            invocation_id = ev.invocation_id
        if ev.output is not None:
            final = ev.output

    if interrupt_id:
        print("  [graph suspended, nothing downstream has run]")
        answer = canned or input("  approve? [approved/denied] ").strip() or "denied"
        resume = types.Part(
            function_response=types.FunctionResponse(
                id=interrupt_id, name="ask_for_approval", response={"decision": answer}
            )
        )
        async for ev in runner.run_async(
            user_id=USER,
            session_id=session.id,
            new_message=types.Content(role="user", parts=[resume]),
            invocation_id=invocation_id,
        ):
            if ev.output is not None:
                final = ev.output

    print(f"\nresult: {final}\n")
    return final


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("message")
    p.add_argument("--limit", type=float, default=50, help="auto approve at or under this amount")
    p.add_argument("--model", default="gemini-flash-latest")
    p.add_argument("--answer", default=None, help="skip the prompt, approved or denied")
    a = p.parse_args()
    asyncio.run(run(a.message, a.model, a.limit, a.answer))
