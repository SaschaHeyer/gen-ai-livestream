import os
from dotenv import load_dotenv, find_dotenv
from google.adk.agents import Agent
from google.adk.tools import load_memory

# --- Configuration (Vertex AI) ---
# Load environment variables from .env file (searches parent directories)
load_dotenv(find_dotenv())

# We use the built-in 'load_memory' tool which allows the agent to search
# the MemoryService for past information.

def set_magic_number(number: int, tool_context=None) -> str:
    """Sets a magic number in the CURRENT session state.
    This number will be forgotten when the session ends.
    """
    if tool_context:
        tool_context.state['magic_number'] = number
        return f"Magic number {number} saved to TEMPORARY session state."
    return "Error: No tool context available."

def get_magic_number(tool_context=None) -> str:
    """Gets the magic number from the CURRENT session state."""
    if tool_context:
        val = tool_context.state.get('magic_number')
        if val:
            return f"The magic number in this session is {val}."
        return "I don't know the magic number (it might be set in a different session)."
    return "Error: No tool context available."

memory_agent = Agent(
    name="memory_agent",
    model="gemini-2.5-flash",
    description="Agent that demonstrates the difference between Session and Memory.",
    instruction="""You are a Memory Demo Agent.

Your goal is to demonstrate the difference between "Session State" (short-term) and "Long-term Memory".

1. **Session State**: Use `set_magic_number` and `get_magic_number`. Explain that this data is fleeting.
2. **Long-term Memory**: If the user asks about facts from the past (like "what is my favorite color"), use the `load_memory` tool to search for it.
   - NOTE: You do NOT need a tool to save to memory. The system automatically saves our conversation to memory when the session ends. You just need to recall it.

Always explain *where* you are getting the information from (e.g., "I found this in your long-term memory..." or "I see this in your current session state...").
""",
    tools=[set_magic_number, get_magic_number, load_memory]
)
