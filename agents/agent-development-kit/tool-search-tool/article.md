# Scaling Google ADK Agents: Implementing Anthropic-style Dynamic Tool Search

The "Tool Search" pattern empowers AI agents to effectively manage hundreds or even thousands of tools by dynamically discovering and loading them strictly on-demand. Instead of overwhelming the model by dumping every possible tool definition into the context window upfront, this approach keeps the context small without missing out on a large number of tools.

Anthropic recently introduced the ["Tool Search" pattern](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool) and discussed strategies for [Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use) to solve this. This mechanism allows the agent to *search* for tools and load them on-demand.

This article demonstrates how to implement this robust, scalable pattern in **Google's Agent Development Kit (ADK)**, enabling your agents to access thousands of tools (including MCP tools) with negligible latency.

## The Challenge

MCP tool definitions provide important context, but as more servers connect, those tokens can add up. Consider a simple three-server setup:

*   **GitHub:** 26 tools (~3,930 tokens)
*   **Linear:** 23 tools (~4,501 tokens)
*   **Playwright:** 22 tools (~2,584 tokens)

That's **71 tools consuming approximately ~11,000 tokens** before the conversation even starts. Add more servers like Slack or Jira, and you're quickly approaching significant token overhead per turn.

But token cost isn't the only issue. The most common failures are wrong tool selection and incorrect parameters, especially when tools have similar names across different integrations.

## Discovery and Loading

The core concept is to split tool usage into two phases:

1.  **Discovery:** The agent has access to a lightweight "Search" tool. It queries a local index (using BM25) to find relevant tools based on names and docstrings.
2.  **Loading:** Once the agent identifies a useful tool, it calls a "Load" tool. The system intercepts this call and dynamically injects the *full* tool definition into the agent's context for the next turn.

## Prerequisite: The Advanced Registry

First, we need a registry that can index tools without exposing their heavy JSON schemas to the LLM immediately. We'll use `rank_bm25` for high-performance probabilistic search.

```bash
pip install rank_bm25 google-adk
```

### 1. Building the Registry

```python
import inspect
from typing import Callable, Dict, List, Any
from rank_bm25 import BM25Okapi

class AdvancedToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Any] = {}
        self._descriptions: List[str] = []
        self._tool_names: List[str] = []
        self._bm25 = None

    def register(self, tool: Any):
        """Registers a Python function or ADK BaseTool/MCPTool."""
        # Handle both raw functions and ADK objects
        if hasattr(tool, 'name'):
            name = tool.name
            doc = getattr(tool, 'description', "") or ""
        else:
            name = tool.__name__
            doc = inspect.getdoc(tool) or ""

        # Index a combination of name and docstring for better retrieval
        description = f"{name} {doc}"

        self._tools[name] = tool
        self._tool_names.append(name)
        self._descriptions.append(description)

        # Re-build the BM25 index
        tokenized_corpus = [desc.lower().split(" ") for desc in self._descriptions]
        self._bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query: str, n: int = 3) -> List[str]:
        """Returns lightweight summaries (Name + Docstring snippet)."""
        if not self._bm25: return []

        tokenized_query = query.lower().split(" ")
        top_docs = self._bm25.get_top_n(tokenized_query, self._descriptions, n=n)

        results = []
        for doc in top_docs:
            idx = self._descriptions.index(doc)
            name = self._tool_names[idx]
            summary = doc.split('\n')[0][:100] # Keep it brief!
            results.append(f"{name}: {summary}")
        return results

    def get_tool(self, name: str) -> Any:
        return self._tools.get(name)

registry = AdvancedToolRegistry()
```

## 2. Exposing the System Tools

Instead of giving the agent 100 tools, we give it just two:

```python
def search_available_tools(query: str) -> List[str]:
    """Searches the tool library for useful tools.

    Use this when you don't have a tool for a specific task.
    Returns a list of 'ToolName: Description'.

    Args:
        query: Search keywords (e.g., 'weather', 'ticket', 'database').
    """
    return registry.search(query)

def load_tool(tool_name: str) -> str:
    """Loads a specific tool into your context.

    Call this after finding a tool with 'search_available_tools'.

    Args:
        tool_name: The exact name of the tool to load.
    """
    # This function is a signal for the callback.
    tool = registry.get_tool(tool_name)
    if tool:
        return f"Tool '{tool_name}' loaded successfully."
    return f"Error: Tool '{tool_name}' not found."
```

## 3. The Dynamic Injection Callback

This is the "brain" of the operation. We use ADK's `after_tool_callback` to intercept the `load_tool` execution and modify the agent's capabilities in real-time.

```python
from google.adk.tools import tool_context

async def dynamic_loader_callback(tool_obj, tool_args, tool_ctx, tool_result):
    # 1. Identify if the executed tool was 'load_tool'
    tool_name = getattr(tool_obj, 'name', str(tool_obj))

    if "load_tool" in tool_name:
        requested_name = tool_args.get('tool_name')

        # 2. Fetch the heavy tool definition from registry
        new_tool = registry.get_tool(requested_name)

        if new_tool:
            # 3. Inject it into the Agent's live toolset
            # We verify duplicates to keep context clean
            current_names = [getattr(t, 'name', t.__name__) for t in my_agent.tools]

            if requested_name not in current_names:
                my_agent.tools.append(new_tool)
                print(f"[System] Injected '{requested_name}' into context.")

    return tool_result
```

## 4. Integration with MCP (Linear, Github, etc.)

This pattern is perfect for MCP (Model Context Protocol). You can connect to an MCP server, fetch *all* available tools at startup, index them, but only load them when the agent needs them.

```python
from google.adk.tools import McpToolset

async def setup_mcp_registry():
    # Initialize your MCP connection
    linear_mcp = McpToolset(connection_params=...)

    # Fetch all tools (but don't give them to the agent yet!)
    tools = await linear_mcp.get_tools()

    # Register them for search
    for tool in tools:
        registry.register(tool)

# Initialize Agent with ONLY the system tools
my_agent = Agent(
    name="ScalableAgent",
    tools=[search_available_tools, load_tool],
    after_tool_callback=dynamic_loader_callback
)
```

## Performance

We benchmarked this architecture using the **Official GitHub MCP Server** (26 tools) vs. the standard "load everything" approach.

```text
--- Scenario A: Standard (Load All Tools) ---
Total Payload Size (approx chars): 15696
Estimated Tokens (chars / 4): 3924

--- Scenario B: Dynamic (Search + 1 Tool) ---
Total Payload Size (approx chars): 857
Estimated Tokens (chars / 4): 214

--- RESULTS ---
Context Saved: 14839 chars (~3709 tokens)
Percentage Reduction: 94.54%
```

## Alternative Approaches

While BM25 provides a robust, keyword-based retrieval mechanism that works exceptionally well for technical function names and documentation, it's not the only way to solve the discovery problem. Vector embeddings (semantic search) are the most common alternative, allowing for fuzzy conceptual matching (e.g., "find bugs" matching `get_issue`).

However, we are interested in exploring even more novel retrieval strategies. If you have ideas for tool discovery that go beyond traditional keyword search or vector embeddings, **ping me on LinkedIn**. We'd love to discuss how to further optimize agentic tool selection.

## Conclusion

By implementing a registry-based search and dynamic injection pattern, you can make Google ADK agents significantly more powerful and cost-effective. This approach allows your agents to scale to enterprise-level complexity without hitting context limits or suffering from tool-selection confusion.
