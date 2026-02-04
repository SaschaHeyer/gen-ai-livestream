import logging
import os
import datetime
from dotenv import load_dotenv, find_dotenv

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams

# --- Configuration (Vertex AI) ---
# Load environment variables from .env file
load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

def get_current_date() -> str:
    """Returns the current date in YYYY-MM-DD format."""
    return datetime.date.today().strftime("%Y-%m-%d")

SYSTEM_INSTRUCTION = (
    "You are a specialized assistant for flight bookings. "
    "Your sole purpose is to use the provided tools to search for flights, retrieve flight details, and make bookings. "
    "Use 'search_flights' to find options based on origin, destination, and date. "
    "Use 'get_flight_details' to get more information about a specific flight. "
    "Use 'book_flight' to confirm a booking for a passenger. "
    "If the user provides a relative date (e.g., 'tomorrow', 'next Friday'), use the 'get_current_date' tool to calculate the correct date in YYYY-MM-DD format. "
    "If the user asks about anything other than flights, politely state that you can only assist with flight-related queries. "
)

# Use the deployed Cloud Run MCP server
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "https://flight-mcp-server-234439745674.us-central1.run.app/mcp")

logger.info(f"--- 🔧 Loading MCP tools from MCP Server at {MCP_SERVER_URL}... ---")
logger.info("--- 🤖 Creating ADK Flight Agent... ---")

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="flight_mcp_agent",
    description="An agent that can search and book flights using an MCP server.",
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        get_current_date,
        MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=MCP_SERVER_URL
            )
        )
    ],
)
