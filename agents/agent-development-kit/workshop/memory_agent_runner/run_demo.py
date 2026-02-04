import asyncio
import os
import sys
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env file (searches parent directories)
load_dotenv(find_dotenv())

# Ensure the current directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.genai import types
from agent import memory_agent

async def run_turn(runner, user_id, session_id, text):
    """Helper to run one turn of conversation"""
    print(f"\n[User ({session_id})]: {text}")
    message = types.Content(role="user", parts=[types.Part(text=text)])
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=message):
        if event.is_final_response() and event.content and event.content.parts:
            print(f"[Agent]: {event.content.parts[0].text}")

async def main():
    print("--- 🧠 Memory vs Session Demo ---")
    
    # 1. Setup Services
    # We need BOTH session service (for now) and memory service (for the past)
    session_service = InMemorySessionService()
    memory_service = InMemoryMemoryService()
    
    runner = Runner(
        agent=memory_agent,
        app_name="memory_demo",
        session_service=session_service,
        memory_service=memory_service 
    )
    
    user_id = "sascha"

    # ==========================================
    # PART 1: SESSION A (Teaching Phase)
    # ==========================================
    session_a_id = "session_A"
    print(f"\n--- 🟢 Starting SESSION A (ID: {session_a_id}) ---")
    await session_service.create_session(app_name="memory_demo", user_id=user_id, session_id=session_a_id)
    
    # A. Set Session State (Short-term)
    await run_turn(runner, user_id, session_a_id, "Set the magic number to 42.")
    
    # B. Provide Fact for Memory (Long-term)
    await run_turn(runner, user_id, session_a_id, "My favorite color is Blue. Please remember that.")
    
    # C. Verify Session State works inside Session A
    await run_turn(runner, user_id, session_a_id, "What is the magic number?")

    print(f"\n--- 🛑 Ending SESSION A ---")
    
    # CRITICAL STEP: INGESTION
    # We must explicitly tell the Memory Service to "learn" from this completed session.
    # In a real app, this might happen automatically on session close or via a background job.
    print("... 💾 Saving Session A to Long-Term Memory ...")
    session_a = await session_service.get_session(app_name="memory_demo", user_id=user_id, session_id=session_a_id)
    await memory_service.add_session_to_memory(session_a)


    # ==========================================
    # PART 2: SESSION B (Recall Phase)
    # ==========================================
    session_b_id = "session_B"
    print(f"\n--- 🔵 Starting SESSION B (ID: {session_b_id}) ---")
    print("(This is a completely new conversation thread. The 'Magic Number' should be lost, but 'Favorite Color' should be found.)")
    
    await session_service.create_session(app_name="memory_demo", user_id=user_id, session_id=session_b_id)
    
    # A. Test Session State Persistence (Should FAIL to find number)
    await run_turn(runner, user_id, session_b_id, "What is the magic number?")
    
    # B. Test Long-Term Memory (Should SUCCEED to find color)
    await run_turn(runner, user_id, session_b_id, "Do you know what my favorite color is?")

if __name__ == "__main__":
    asyncio.run(main())
