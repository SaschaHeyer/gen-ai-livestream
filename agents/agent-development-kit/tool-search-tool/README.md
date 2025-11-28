# Tool Search & MCP Inspection Utilities

This folder contains Python scripts to experiment with the **Model Context Protocol (MCP)** and **Dynamic Tool Loading (Tool Search)** using the Google Gen AI ADK.

## Prerequisites

*   **Python 3.10+**
*   **Node.js & npm** (required to run the MCP servers via `npx`)
*   **Google API Key** (for Gemini models)
*   **GitHub Personal Access Token** (for the GitHub MCP server)

### Dependencies
Ensure you have the necessary Python packages installed:
```bash
pip install rank_bm25 mcp google-genai
# Note: This assumes you have the 'google.adk' package installed or available in your python path.
```

---

## 1. MCP Tool Inspector (`inspect_mcp_tools.py`)

A utility to connect to any standard MCP server (running over stdio) and inspect the tools it exposes. It calculates the estimated token usage for each tool's definition, helping you optimize your agent's context window.

### Usage

You need to provide the command to start the MCP server using `--command` and its arguments using `--args`.

**Example: Inspecting the GitHub MCP Server**

```bash
# 1. Export necessary tokens for the MCP server
export GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here

# 2. Run the inspector
python inspect_mcp_tools.py --command npx --args "-y @modelcontextprotocol/server-github"
```

**Output:**
It will print a table listing every tool found, its character count, and estimated token count.

```text
--- Found 26 Tools ---
TOOL NAME                                     | CHARS    | TOKENS  
----------------------------------------------------------------------
create_issue                                  | 1250     | 312     
get_issue                                     | 890      | 222     
...
----------------------------------------------------------------------
TOTAL                                         | 25430    | 6357    
GRAND TOTAL TOKENS: ~6357
```

---

## 2. GitHub Agent Demo (`github_demo.py`)

This script demonstrates the **Tool Search** pattern.

### The Problem
The GitHub MCP server provides ~26 tools. Loading all of them into the LLM's system prompt consumes significant tokens (~6k+) and can confuse the model.

### The Solution
The Agent starts with **zero** GitHub tools. It only has two system tools:
1.  `search_tools(query)`: Searches the local BM25 index of available MCP tools.
2.  `load_tool(name)`: Dynamically injects a tool into the Agent's context at runtime.

### Usage

```bash
# 1. Export API Keys
export GOOGLE_API_KEY=AIza...
export GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...

# 2. Run the demo
python github_demo.py
```

### Execution Flow
1.  **Connect**: Connects to the GitHub MCP server and fetches all tool definitions (without giving them to the Agent yet).
2.  **Index**: Builds a local BM25 search index of the tool descriptions.
3.  **Run**: Starts the Agent with the prompt: *"Get details for issue .../issues/6"*.
4.  **Autonomous Loop**:
    *   Agent calls `search_tools('github issues')`.
    *   Agent sees `get_issue` in results.
    *   Agent calls `load_tool('get_issue')`.
    *   **Callback**: The script injects the real `get_issue` function into the Agent.
    *   Agent calls `get_issue(owner=..., repo=..., number=6)`.
    *   Agent summarizes the JSON result for the user.

---

## 3. Context Benchmark (`context_benchmark.py`)

This script compares the token usage of loading *all* available tools versus using the dynamic "Tool Search" pattern.

### Usage

```bash
# 1. Export API Keys
export GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...

# 2. Run the benchmark
python context_benchmark.py
```

### Benchmark Results (GitHub MCP)

The following results demonstrate the massive efficiency gain of using Dynamic Tool Search:

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