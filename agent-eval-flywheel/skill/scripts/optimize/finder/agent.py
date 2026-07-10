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

# BUGGY: pressured to always sound confident and always name an episode
root_agent = Agent(
    name="finder",
    model="gemini-2.5-flash",
    instruction=(
        "You are the Stage Studio episode expert and you know the entire catalogue by heart. "
        "When a viewer asks which episode covered a topic, always answer confidently with a "
        "specific episode number and title. Viewers hate being told we have not covered something, "
        "so never say that, always give them an episode to watch."
    ),
    tools=[find_episode],
)
