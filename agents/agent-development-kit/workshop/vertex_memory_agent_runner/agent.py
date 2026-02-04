import os
from dotenv import load_dotenv, find_dotenv
from google.adk.agents import Agent
from google.adk.tools.preload_memory_tool import PreloadMemoryTool

# --- Configuration (Vertex AI) ---
# Load environment variables from .env file (searches parent directories)
load_dotenv(find_dotenv())

async def auto_save_session_to_memory_callback(callback_context):
    """Automatically saves the session to memory after the agent finishes."""
    if callback_context._invocation_context.memory_service:
        print("... ☁️ Auto-saving Session to Vertex AI Memory Bank ...")
        await callback_context._invocation_context.memory_service.add_session_to_memory(
            callback_context._invocation_context.session
        )
        print("✅ Auto-save Complete!")

vertex_memory_agent = Agent(
    name="vertex_memory_agent",
    model="gemini-2.5-flash",
    description="A personalized vacation planner that remembers user preferences.",
    instruction="""You are an expert Vacation Planner. Your goal is to help users plan their dream trips.

You have access to the user's travel history and preferences through your long-term memory (provided via context).

1. **Check Memory First**: Before asking questions, look at the preloaded memory context. If the user has mentioned preferences (e.g., "likes hiking", "hates spicy food", "budget traveler") or past trips in previous conversations, use that information to tailor your suggestions.
2. **Personalize**: If you find relevant history, explicitly acknowledge it to show you remember them (e.g., "Welcome back! Since you enjoyed your trip to Mars, maybe you'd like...").
3. **Plan**: Help them plan destinations, activities, and logistics.
4. **Learn**: Pay attention to new preferences they share in this conversation so they can be saved for next time.
""",
    tools=[PreloadMemoryTool()],
    after_agent_callback=auto_save_session_to_memory_callback
)
