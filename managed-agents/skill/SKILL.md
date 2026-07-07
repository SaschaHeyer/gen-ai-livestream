---
name: managed-agents
description: Use this skill when running Gemini API Managed Agents through the Interactions API, especially background execution (background=True, poll and reconnect by interaction id), attaching remote MCP servers as tools, custom function calling with the requires_action flow, and reusing a server side sandbox across turns with environment_id. Covers the antigravity managed agent, the client.interactions SDK surface, and the agent vs model gotcha. SDKs and tools used, google-genai Python SDK (client.interactions), Python 3.10+, Gemini API key.
---

# Gemini Managed Agents Skill

Managed Agents run server side in a Google hosted sandbox that can write files and run code for you. The Interactions API drives them, through `client.interactions` in the `google-genai` SDK. This skill covers the four capabilities that shipped in July 2026 on top of the existing managed agents, background execution, remote MCP tools, custom functions, and credential refresh.

> [!IMPORTANT]
> The managed agent is `antigravity-preview-05-2026`, powered by Gemini 3.5 Flash. Pass it in the `agent` field, never `model`. Passing it as `model` returns HTTP 400, "antigravity-preview-05-2026 is not supported as a model. Use it as an agent instead." Google's own background execution doc shows `model=` here, which throws, while the antigravity agent doc and Google's Interactions API skill both correctly use `agent`. The name carries `preview` for a reason, expect it to change, do not hardcode it as permanent.

> [!IMPORTANT]
> `client.interactions` lives in `google-genai` 2.x, which requires Python 3.10 or newer. Install `pip install "google-genai>=2.3.0"`. On the Python 3.9 that ships with macOS, pip caps at 1.47.0, which does not have `client.interactions`, and the samples will `AttributeError`, that is an interpreter version issue, not a missing feature. Managed agent interactions also require `environment="remote"`.

> [!WARNING]
> Managed Agents are not new in July 2026, they already existed. The Interactions API itself went GA in June 2026, but the managed agent model is still Preview, and environment compute is not billed during preview, that will change. You still pay for tokens.

---

## Quick Start

Set the key once, then create a client.

```bash
export GEMINI_API_KEY=your_key_here
```

```python
import os, time
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
AGENT = "antigravity-preview-05-2026"
```

### Background execution, fire and reconnect

Kick off a long task, get an id back immediately, then poll it from anywhere, no held connection.

```python
# fire and forget
inter = client.interactions.create(
    agent=AGENT,
    input="Create a folder named project/ and write hello.py inside that prints hi.",
    environment="remote",
    background=True,
)

interaction_id = inter.id          # your claim ticket
print(inter.status)                # in_progress, it did NOT wait for the work

# later, fresh process, only the id, poll until done
while True:
    rec = client.interactions.get(interaction_id)
    if rec.status != "in_progress":
        break
    time.sleep(2)

# the completed record carries the full step trace, thought, tool call, result
for step in rec.steps:
    print(step.type, getattr(step, "name", ""))
```

> [!WARNING]
> A background interaction that creates its own sandbox returns `environment_id` as `None`, on the create response AND on the completed record, so that sandbox can never be referenced again. Passing an existing `environment_id` INTO a background create works and the files persist. The pattern, seed the sandbox with one foreground turn to get its `environment_id`, then run any number of background turns inside it, see the next block.

> [!TIP]
> To resume a dropped live stream instead of polling, `client.interactions.get(id, stream=True, last_event_id=last_seen)` replays from the last event you saw.

### Reuse a sandbox across turns with environment_id

A foreground interaction returns `environment_id`. Chain the next turn with both `previous_interaction_id` and `environment` to land in the same sandbox with your files intact.

```python
first = client.interactions.create(
    agent=AGENT,
    input="Write notes.txt containing the single line: prep works.",
    environment="remote",
)

second = client.interactions.create(
    agent=AGENT,
    previous_interaction_id=first.id,
    environment=first.environment_id,   # same sandbox, files persist
    input="List the files and show the contents of notes.txt.",
)
```

> [!WARNING]
> Forget `environment` on the chained call and you get a brand new sandbox with none of your files. Both `previous_interaction_id` and `environment` are required together.

### Attach a remote MCP server as a tool

The agent keeps its built in sandbox tools and also gets the remote MCP server's tools in the same interaction.

```python
inter = client.interactions.create(
    agent=AGENT,
    input="What is the weather in Tokyo today? Use the weather tool.",
    environment="remote",
    tools=[{
        "type": "mcp_server",
        "name": "weather",                                  # lowercase alphanumeric
        "url": "https://gemini-api-demos.uc.r.appspot.com/mcp",
        # optional: "headers": {...}, "allowed_tools": [...]
    }],
)
```

> [!WARNING]
> A remote MCP server is a live network dependency inside your agent run. If it is slow, down, or rate limited, the interaction stalls or errors. Treat it like any other flaky upstream, set expectations and have a fallback.

### Custom function calling, the requires_action flow

Add your own tools next to the sandbox tools. The agent pauses at `status == "requires_action"`, you run the pending `function_call` steps, then return each `function_result`.

```python
final = client.interactions.create(
    agent=AGENT,
    previous_interaction_id=inter.id,
    environment=inter.environment_id,
    input=[{
        "type": "function_result",
        "call_id": fc_step.id,       # id of the function_call step you executed
        "result": your_result,
    }],
)
```

## Interaction record shape

`create` and `get` return an `Interaction` object. `inter.steps` is a list of typed step objects, in the order the agent produced them. Which tool-step types appear depends on how the agent solved the task (it may write a file or run code).

| `step.type`             | key attributes                                          |
| ----------------------- | ------------------------------------------------------- |
| `thought`               | `summary`                                               |
| `function_call`         | `name`, `arguments` (dict), `id`                         |
| `function_result`       | `result` (list of text parts), `call_id`, `is_error`     |
| `code_execution_call`   | `arguments.code`, `arguments.language`, `id`             |
| `code_execution_result` | `result` (str), `call_id`, `is_error`                    |
| `model_output`          | `content` (list of text parts, each with `.text`)        |

Statuses seen in prep, `in_progress`, `completed`, `requires_action`.

## Supporting files

- [scripts/agent.py](scripts/agent.py), tiny SDK helper, `create`, `get`, `poll`, `show_steps` (handles both file-write and code-execution step traces). Import it, the three demos below do.
- [scripts/background_run.py](scripts/background_run.py), fire a background task and print the id. Run it, then pass the id to the next one.
- [scripts/reconnect.py](scripts/reconnect.py), `python reconnect.py <id>`, poll by id and print the step trace the agent ran while you were disconnected.
- [scripts/mcp_tool.py](scripts/mcp_tool.py), attach the demo weather MCP server and print what the agent called.
- [requirements.txt](requirements.txt), the one dependency, `google-genai>=2.3.0` (Python 3.10+).

## Documentation Pages

You MUST fetch the matching page below before writing code. These hosted docs are the source of truth for parameters, types, and edge cases, do not rely solely on the examples above. The SDK samples need `google-genai >= 2.3.0` on Python 3.10+, and the background execution page shows `model=` where the working call needs `agent=`.

- https://ai.google.dev/gemini-api/docs/background-execution
- https://ai.google.dev/gemini-api/docs/antigravity-agent
- https://ai.google.dev/gemini-api/docs/interactions-overview
- https://github.com/google-gemini/gemini-skills/tree/main/skills/gemini-interactions-api

## From the episode

Built live on the Friday stream, video link to follow.
