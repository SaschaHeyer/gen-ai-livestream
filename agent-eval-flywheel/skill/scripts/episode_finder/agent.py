"""A tiny Stage Studio helper agent, deliberately buggy so the eval catches it.

The agent answers which livestream episode covered a given topic. It has a
find_episode tool that holds the real answer. The instruction below is the
BUGGY version, it lets the model answer from memory instead of calling the
tool, so tool_trajectory_avg_score will fail. Beat 3 fixes the instruction.
"""

from google.adk.agents import Agent

# The real episode catalogue. The tool is the only source of truth.
_CATALOGUE = {
    "tabular foundation model": {"episode": "e01", "title": "TabFM zero shot tabular"},
    "background agents": {"episode": "e02", "title": "Managed Agents background and remote MCP"},
    "remote mcp": {"episode": "e02", "title": "Managed Agents background and remote MCP"},
    "agent evaluation": {"episode": "e03", "title": "Agent Quality Flywheel eval skill"},
}


def find_episode(topic: str) -> dict:
    """Look up which Stage Studio episode covered a topic.

    Args:
        topic: The subject the viewer is asking about, for example
            "background agents" or "agent evaluation".

    Returns:
        A dict with the episode id and title, or a not_found marker.
    """
    key = topic.strip().lower()
    for name, record in _CATALOGUE.items():
        if name in key or key in name:
            return {"found": True, **record}
    return {"found": False, "topic": topic}


# BUGGY instruction, it invites the model to answer from memory.
root_agent = Agent(
    name="episode_finder",
    model="gemini-2.5-flash",
    description="Tells viewers which Stage Studio episode covered a topic.",
    instruction=(
        "You are the Stage Studio episode helper. When a viewer asks which "
        "episode covered a topic, tell them the episode id and title. You know "
        "the show well."
    ),
    tools=[find_episode],
)
