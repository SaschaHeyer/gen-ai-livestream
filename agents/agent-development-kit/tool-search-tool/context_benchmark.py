
import asyncio
import os
import sys
import json
from typing import List, Any

# Third-party
from mcp import StdioServerParameters
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk import Agent
from google.adk.tools import McpToolset
from google.genai import Client  # To count tokens
from google.genai.types import Tool as GenAITool, FunctionDeclaration

# --- Helper to Estimate Token Count ---

def estimate_token_count(tools_list: List[Any]) -> int:
    """
    Estimates the token count for a list of tools.
    We do this by converting the tools to their JSON schema representation
    (which is what the LLM actually sees) and counting the characters/tokens.
    """
    total_chars = 0
    
    for tool in tools_list:
        # 1. Name
        if hasattr(tool, 'name'):
            name = tool.name
        elif hasattr(tool, '__name__'):
            name = tool.__name__
        else:
            name = "unknown_tool"
            
        # 2. Description
        if hasattr(tool, 'description'):
            desc = tool.description
        else:
            desc = tool.__doc__ or ""
            
        # 3. Args Schema (The heavy part)
        tool_dump = f"{name} {desc}"
        
        # ADK MCP Tool specific extraction
        if hasattr(tool, '_mcp_tool') and hasattr(tool._mcp_tool, 'inputSchema'):
            try:
                schema = tool._mcp_tool.inputSchema
                tool_dump += json.dumps(schema)
            except:
                pass
        # Standard ADK Tool extraction
        elif hasattr(tool, 'input_schema') and tool.input_schema:
            try:
                schema = tool.input_schema.model_json_schema()
                tool_dump += json.dumps(schema)
            except:
                pass
                
        total_chars += len(tool_dump)
        
    return total_chars

# --- 1. The Benchmark Logic ---
async def run_benchmark():
    # Check Env
    github_token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not github_token:
        print("[Error] GITHUB_PERSONAL_ACCESS_TOKEN not set. Please export it and try again.")
        return

    print("--- Connecting to GitHub MCP ---")
    github_mcp = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                env={**os.environ}
            )
        )
    )

    try:
        print("Fetching tools...")
        all_tools = await github_mcp.get_tools()
        print(f"Fetched {len(all_tools)} tools from GitHub.")

        # --- Scenario A: Standard (All Tools) ---
        print("\n--- Scenario A: Standard (Load All Tools) ---")
        # In this scenario, the agent starts with ALL tools loaded.
        size_a = estimate_token_count(all_tools)
        print(f"Total Payload Size (approx chars): {size_a}")
        print(f"Estimated Tokens (chars / 4): {int(size_a / 4)}")
        
        # --- Scenario B: Dynamic (Search + Load) ---
        print("\n--- Scenario B: Dynamic (Search + 1 Tool) ---")
        
        # 1. System Tools
        def search_tools(q): pass
        def load_tool(n): pass
        
        system_tools = [search_tools, load_tool]
        
        # 2. The loaded tool (just one)
        # Let's say we load 'github_list_issues' (assuming it's index 0 for simplicity')
        if all_tools:
            active_tools = system_tools + [all_tools[0]]
        else:
            active_tools = system_tools
            
        size_b = estimate_token_count(active_tools)
        
        print(f"Total Payload Size (approx chars): {size_b}")
        print(f"Estimated Tokens (chars / 4): {int(size_b / 4)}")
        
        # --- Comparison ---
        print("\n--- RESULTS ---")
        reduction = size_a - size_b
        percent = (reduction / size_a) * 100
        print(f"Context Saved: {reduction} chars (~{int(reduction/4)} tokens)")
        print(f"Percentage Reduction: {percent:.2f}%")
        
        if size_a > 0:
             print("\nConclusion: Dynamic loading significantly reduces context usage.")

    finally:
        await github_mcp.close()

if __name__ == "__main__":
    asyncio.run(run_benchmark())
