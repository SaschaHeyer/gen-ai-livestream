"""Beat 3, bolt a remote MCP server onto the agent as a tool.

The agent keeps its built in sandbox tools (its hands) and also gets a remote
MCP server (a phone it can call out on). Here it uses Google's demo weather MCP.
"""
import agent

rec = agent.create(
    input="What is the weather in Berlin today? Use the weather tool.",
    tools=[{
        "type": "mcp_server",
        "name": "weather",   # lowercase alphanumeric
        "url": "https://gemini-api-demos.uc.r.appspot.com/mcp",
    }],
)
print("status:", rec.status)
agent.show_steps(rec)
