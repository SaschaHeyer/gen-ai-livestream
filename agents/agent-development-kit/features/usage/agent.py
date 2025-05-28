import os
import asyncio
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

APP_NAME = "token_usage_demo"
USER_ID = "user_123"
SESSION_ID = "token_session_abc"
MODEL_ID = "gemini-2.0-flash-exp"

def log_token_usage(response, query: str):
    """Log token usage information from LlmResponse"""
    if hasattr(response, 'usage_metadata') and response.usage_metadata:
        usage = response.usage_metadata
        print(f"\n=== TOKEN USAGE FOR QUERY: '{query}' ===")
        print(f"Input tokens: {getattr(usage, 'prompt_token_count', 'N/A')}")
        print(f"Output tokens: {getattr(usage, 'candidates_token_count', 'N/A')}")
        print(f"Total tokens: {getattr(usage, 'total_token_count', 'N/A')}")
        print("=" * 50)
    else:
        print(f"No token usage data available for query: '{query}'")

simple_agent = LlmAgent(
    model=MODEL_ID,
    name='TokenUsageAgent',
    instruction="""You are a helpful assistant. Keep your responses concise and informative. 
    Answer user questions directly and clearly."""
)

session_service = InMemorySessionService()

runner = Runner(
    agent=simple_agent,
    app_name=APP_NAME,
    session_service=session_service
)

async def chat_with_token_logging_async(query: str):
    """Send a query to the agent and log token usage"""
    print(f"\nUser: {query}")
    content = types.Content(role='user', parts=[types.Part(text=query)])
    
    # Create session asynchronously
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        state={}
    )
    
    events = runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content)
    
    for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            response_text = "".join(part.text for part in event.content.parts if part.text)
            print(f"Agent: {response_text}")
            
            # Log token usage if available
            if hasattr(event, 'response') and event.response:
                log_token_usage(event.response, query)
            elif hasattr(event, 'usage_metadata'):
                log_token_usage(event, query)
            else:
                print(f"No token usage data found in event for query: '{query}'")
            break
        elif event.is_error():
            print(f"Error: {event.error_details}")
            break

def chat_with_token_logging(query: str):
    """Synchronous wrapper for async chat function"""
    asyncio.run(chat_with_token_logging_async(query))

if __name__ == "__main__":
    print("=== Google ADK Token Usage Demo ===")
    print("Type 'quit' to exit")
    
    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ["quit", "exit"]:
                break
            if user_input.strip():
                chat_with_token_logging(user_input)
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
    
    # Cleanup
    try:
        asyncio.run(session_service.delete_session(APP_NAME, USER_ID, SESSION_ID))
        print("Session cleaned up.")
    except Exception as e:
        print(f"Cleanup error: {e}")