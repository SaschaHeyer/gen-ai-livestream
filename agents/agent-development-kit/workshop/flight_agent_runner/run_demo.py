import asyncio
import os
import sys

# Ensure the current directory is in the path so we can import the agent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from agent import flight_agent

async def main():
    print("--- 🏃 Flight Agent Runner Demo ---")
    
    # 1. Initialize Session Service
    # This service manages the conversation history and state in memory.
    session_service = InMemorySessionService()
    
    # 2. Initialize Runner
    # The Runner orchestrates the agent's execution, connecting it with the session service.
    runner = Runner(
        agent=flight_agent,
        app_name="flight_runner_demo",
        session_service=session_service
    )
    
    # 3. Create a Session
    # We explicitly create a session to track this specific conversation.
    session_id = "demo_session_001"
    user_id = "user_123"
    await session_service.create_session(
        app_name="flight_runner_demo",
        user_id=user_id,
        session_id=session_id
    )
    
    print(f"✅ Session Created (ID: {session_id})")
    print("Type 'exit' to quit.\n")
    
    # 4. Interactive Loop
    while True:
        try:
            user_input = input("You: ")
        except EOFError:
            break
            
        if user_input.lower() in ["exit", "quit"]:
            break
            
        # Create the content object for the user's message
        message = types.Content(role="user", parts=[types.Part(text=user_input)])
        
        # 5. Run the Agent via Runner
        # run_async handles the loop of thinking -> tool calls -> response
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message
        ):
            # The runner emits events. We only want to print the final response to the user.
            if event.is_final_response() and event.content and event.content.parts:
                print(f"Agent: {event.content.parts[0].text}")

if __name__ == "__main__":
    asyncio.run(main())
