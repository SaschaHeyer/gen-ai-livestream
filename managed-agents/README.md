# Managed Agents, background execution and remote MCP

Gemini API Managed Agents run server side in a Google hosted sandbox. This episode covers the July 2026 upgrades, background execution (fire a task, get an id, reconnect later), attaching remote MCP servers as tools, custom function calling, and reusing a sandbox across turns.

The skill and all runnable code live in [skill/](skill/).

- [skill/SKILL.md](skill/SKILL.md), the skill, current facts, quick start, gotchas inline.
- [skill/scripts/](skill/scripts/), the three verified demos plus the shared SDK helper they import.
- [skill/requirements.txt](skill/requirements.txt), one dependency, `requests`.

Install for your agent.

```
npx skills add <this-repo> --skill managed-agents
```

Run the demos. Needs Python 3.10 or newer, `client.interactions` lives in `google-genai` 2.x.

```
export GEMINI_API_KEY=your_key_here
pip install -r skill/requirements.txt     # google-genai>=2.3.0
cd skill/scripts
python background_run.py          # prints an interaction id
python reconnect.py <that-id>     # reconnects and shows the step trace
python mcp_tool.py                # attaches the demo weather MCP server
```
