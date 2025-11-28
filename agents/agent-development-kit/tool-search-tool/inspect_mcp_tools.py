
import asyncio
import os
import json
import sys
import argparse
import traceback
from mcp import StdioServerParameters
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools import McpToolset

def calculate_tokens(text: str) -> int:
    """Estimates token count (chars / 4)."""
    return int(len(text) / 4)

async def inspect_mcp(command: str, args: list[str], env: dict = None):
    print(f"--- Connecting to MCP Server: {command} {' '.join(args)} ---")
    
    # Merge provided env with system env (to pass tokens/keys)
    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    mcp_toolset = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=command,
                args=args,
                env=run_env
            )
        )
    )

    try:
        print("Fetching tools...")
        try:
            all_tools = await mcp_toolset.get_tools()
        except Exception as e:
            print(f"Failed to fetch tools. The MCP server might require specific env vars (tokens).")
            print(f"Error: {e}")
            return

        if not all_tools:
            print("No tools found!")
            return

        print(f"\n--- Found {len(all_tools)} Tools ---")
        print(f"{ 'TOOL NAME':<45} | {'CHARS':<8} | {'TOKENS':<8}")
        print("-" * 70)

        grand_total_chars = 0

        for tool in all_tools:
            # 1. Get Schema String
            schema_str = ""
            if hasattr(tool, '_mcp_tool') and hasattr(tool._mcp_tool, 'inputSchema'):
                try:
                    schema = tool._mcp_tool.inputSchema
                    schema_str = json.dumps(schema)
                except: pass
            elif hasattr(tool, 'input_schema') and tool.input_schema:
                try:
                    schema = tool.input_schema.model_json_schema()
                    schema_str = json.dumps(schema)
                except: pass
            
            # 2. Construct full payload
            payload = f"{tool.name} {tool.description} {schema_str}"
            
            char_count = len(payload)
            token_count = calculate_tokens(payload)
            grand_total_chars += char_count
            
            # Truncate name if too long for table
            display_name = (tool.name[:42] + '..') if len(tool.name) > 42 else tool.name
            
            print(f"{display_name:<45} | {char_count:<8} | {token_count:<8}")

        print("-" * 70)
        total_tokens = int(grand_total_chars / 4)
        print(f"{ 'TOTAL':<45} | {grand_total_chars:<8} | {total_tokens:<8}")
        print(f"GRAND TOTAL TOKENS: ~{total_tokens}")

    except Exception:
        traceback.print_exc()
    finally:
        await mcp_toolset.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect tools from any MCP server.")
    parser.add_argument("--command", required=True, help="Executable command (e.g., npx, python, uv)")
    parser.add_argument("--args", required=True, help="Arguments for the command (as a single string)")
    
    # Optional: Allow passing extra env vars via CLI if needed
    parser.add_argument("--env", help="JSON string of env vars")

    args = parser.parse_args()
    
    # Split args string into list
    # e.g. "-y package" -> ["-y", "package"]
    cmd_args = args.args.split(" ")
    
    # Parse env JSON if provided
    env_vars = None
    if args.env:
        try:
            env_vars = json.loads(args.env)
        except json.JSONDecodeError as e:
            print(f"Error parsing --env JSON: {e}")
            sys.exit(1)
    
    asyncio.run(inspect_mcp(args.command, cmd_args, env=env_vars))
