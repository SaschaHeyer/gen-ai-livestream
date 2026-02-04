import asyncio
import os
import sys
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

# Ensure the current directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
# IMPORT THE VERTEX AI MEMORY SERVICE
from google.adk.memory import VertexAiMemoryBankService
from google.genai import types
from agent import vertex_memory_agent

async def run_turn(runner, user_id, session_id, text):
    """Helper to run one turn of conversation"""
    print(f"\n[User ({session_id})]: {text}")
    message = types.Content(role="user", parts=[types.Part(text=text)])
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=message):
        if event.is_final_response() and event.content and event.content.parts:
            print(f"[Agent]: {event.content.parts[0].text}")

async def main():
    print("--- ☁️ Vertex AI Memory Bank Demo ---")

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

    if not project_id:
        print("❌ Error: GOOGLE_CLOUD_PROJECT env var is not set.")
        return

    # 1. Setup Services
    # We still use InMemorySessionService for the active chat (fast, cheap)
    session_service = InMemorySessionService()

    # CRITICAL: Use VertexAiMemoryBankService for Long-Term Memory
    # This requires an Agent Engine ID from Vertex AI.
    agent_engine_id = os.getenv("AGENT_ENGINE_ID")

    if not agent_engine_id:
        print("❌ Error: AGENT_ENGINE_ID env var is not set.")
        print("Please create an Agent Engine in Vertex AI and set the variable.")
        return

    print(f"Connecting to Vertex AI Memory Bank via Agent Engine ID: {agent_engine_id}")

    memory_service = VertexAiMemoryBankService(
        project=project_id,
        location=location,
        agent_engine_id=agent_engine_id
    )

    runner = Runner(
        agent=vertex_memory_agent,
        app_name="vertex_memory_demo",
        session_service=session_service,
        memory_service=memory_service
    )

    user_id = "sascha_vertex_user"

    # ==========================================
    # PART 1: SESSION A (Teaching Phase)
    # ==========================================
    #session_a_id = "session_vertex_A"
    #print(f"\n--- 🟢 Starting SESSION A (ID: {session_a_id}) ---")
    #await session_service.create_session(app_name="vertex_memory_demo", user_id=user_id, session_id=session_a_id)

    #await run_turn(runner, user_id, session_a_id, "I am planning a trip to Mars in 2030.")

    #print(f"\n--- 🛑 Ending SESSION A ---")
    # Note: Memory saving is now handled automatically by the after_agent_callback in agent.py


    # ==========================================
    # PART 2: SESSION B (Recall Phase)
    # ==========================================
    session_b_id = "session_vertex_B"
    print(f"\n--- 🔵 Starting SESSION B (ID: {session_b_id}) ---")
    print("(Querying Vertex AI Memory Bank to find the trip details...)")

    await session_service.create_session(app_name="vertex_memory_demo", user_id=user_id, session_id=session_b_id)

    await run_turn(runner, user_id, session_b_id, "Where am I planning to go in 2030?")

if __name__ == "__main__":
    asyncio.run(main())
