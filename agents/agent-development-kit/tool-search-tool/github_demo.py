
import asyncio
import os
import sys
import inspect
from typing import List, Dict, Any

# Third-party imports
from rank_bm25 import BM25Okapi
from mcp import StdioServerParameters
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams

# Google ADK imports
from google.adk import Agent
from google.adk.tools import McpToolset, tool_context
from google.adk.runners import InMemoryRunner

# --- 1. The Advanced Tool Registry (BM25) ---

class AdvancedToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Any] = {}
        self._descriptions: List[str] = []
        self._tool_names: List[str] = []
        self._bm25 = None

    def register(self, tool: Any):
        """Registers a tool and updates the search index."""
        # Handle ADK/MCP Tool objects (which have .name) vs Python functions
        if hasattr(tool, 'name'):
            name = tool.name
            # ADK tools often have description in .description or .__doc__
            doc = getattr(tool, 'description', "") or inspect.getdoc(tool) or ""
        else:
            name = tool.__name__
            doc = inspect.getdoc(tool) or ""

        description = f"{name} {doc}"

        self._tools[name] = tool
        self._tool_names.append(name)
        self._descriptions.append(description)

        # Re-build index
        tokenized_corpus = [desc.lower().split(" ") for desc in self._descriptions]
        self._bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query: str, n: int = 3) -> List[str]:
        if not self._bm25: return []
        tokenized_query = query.lower().split(" ")
        top_docs = self._bm25.get_top_n(tokenized_query, self._descriptions, n=n)

        results = []
        for doc in top_docs:
            idx = self._descriptions.index(doc)
            name = self._tool_names[idx]
            summary = doc.split('\n')[0][:120]
            results.append(f"{name}: {summary}")
        return results

    def get_tool(self, name: str) -> Any:
        return self._tools.get(name)

registry = AdvancedToolRegistry()

# --- 2. System Tools (Exposed to Agent) ---

def search_tools(query: str) -> List[str]:
    """Searches the external tool library for useful tools.

    Args:
        query: Keywords describing what you want to do (e.g., "github issues", "read file").
    """
    print(f"\n[Agent Action] Searching for: '{query}'")
    return registry.search(query, n=5)

def load_tool(tool_name: str) -> str:
    """Loads a specific tool into your active toolkit.

    Args:
        tool_name: The exact name of the tool to load (found via search_tools).
    """
    # This is a placeholder signal for the callback
    return f"Requesting load for {tool_name}..."

# --- 3. The Dynamic Callback ---

async def dynamic_loader_callback(tool, args, tool_context, tool_response):
    tool_name = getattr(tool, 'name', str(tool))

    # Intercept 'load_tool' calls
    if "load_tool" in tool_name:
        requested_name = args.get('tool_name')
        new_tool = registry.get_tool(requested_name)

        if new_tool:
            # Check if already loaded
            current_names = []
            for t in my_agent.tools:
                if hasattr(t, 'name'): current_names.append(t.name)
                elif hasattr(t, '__name__'): current_names.append(t.__name__)

            if requested_name not in current_names:
                # INJECT THE TOOL
                my_agent.tools.append(new_tool)
                print(f"[System] Successfully injected '{requested_name}' into Agent context.")
                return f"Tool '{requested_name}' is now loaded and ready to use."
            else:
                return f"Tool '{requested_name}' was already loaded."
        else:
            return f"Error: Tool '{requested_name}' not found in registry."

    return tool_response

# --- 4. Main Setup & Execution ---

async def main():
    print("--- 1. Initializing GitHub MCP Connection ---")

    github_mcp = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                env={**os.environ} # Pass env to npx so it sees the Token
            )
        )
    )

    try:
        print("--- 2. Fetching tools from GitHub MCP (this may take a moment)... ---")
        # Get all tools, but DO NOT add them to the agent yet.
        all_github_tools = await github_mcp.get_tools()

        print(f"Received {len(all_github_tools)} tools from GitHub.")

        print("--- 3. Indexing tools into BM25 Registry ---")
        for tool in all_github_tools:
            registry.register(tool)
            # Optional: Print some names to prove it works
            # print(f"  Indexed: {tool.name}")

        print("--- 4. Starting Agent with Minimal Context ---")
        global my_agent
        my_agent = Agent(
            name="GitHubManager",
            model="gemini-2.5-flash",
            tools=[search_tools, load_tool],
            after_tool_callback=dynamic_loader_callback
        )

        print(f"Initial Active Tools: {[t.__name__ for t in my_agent.tools]}")

        # 5. Run Real Agent
        print("\n=== Scenario: User asks 'Get details for issue https://github.com/SaschaHeyer/gen-ai-livestream/issues/6' ===")
        user_prompt = "Get details for issue https://github.com/SaschaHeyer/gen-ai-livestream/issues/6"

        print(f"\n>>> Sending prompt to Agent: \"{user_prompt}\"")
        print(">>> Agent is running (Searching -> Loading -> Executing)...")

        # Initialize the Runner (handles session, context, and execution loop)
        runner = InMemoryRunner(agent=my_agent)

        # Run the agent in debug mode (prints events to stdout)
        await runner.run_debug(user_prompt)

        print("\n\n[SUCCESS] Agent execution complete.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n[Error] An error occurred: {e}")
    finally:
        # Cleanup MCP connection
        await github_mcp.close()

if __name__ == "__main__":
    asyncio.run(main())
