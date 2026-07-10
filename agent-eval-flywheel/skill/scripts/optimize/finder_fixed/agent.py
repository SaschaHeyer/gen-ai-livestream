from google.adk.agents import Agent

_CATALOGUE = {
    "background agents": {"episode": "e02", "title": "Managed Agents background and remote MCP"},
    "agent evaluation": {"episode": "e03", "title": "Agent Quality Flywheel eval skill"},
}

def find_episode(topic: str) -> dict:
    key = topic.strip().lower()
    for name, record in _CATALOGUE.items():
        if name in key or key in name:
            return {"found": True, **record}
    return {"found": False, "topic": topic}

# FIXED: only trust the tool, admit when a topic is not covered
root_agent = Agent(
    name="finder_fixed",
    model="gemini-2.5-flash",
    instruction=(
        "You are the Stage Studio episode helper. Only use what the find_episode tool returns. "
        "If it returns found=false, tell the viewer we have not covered that topic yet, and never "
        "invent or guess an episode number or title."
    ),
    tools=[find_episode],
)
