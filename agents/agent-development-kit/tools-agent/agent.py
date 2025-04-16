from google.adk.agents import Agent
from google.genai import types

from .tools import (
    get_current_time,
)

root_agent = Agent(
    name="time_agent",
    model="gemini-2.0-flash-exp",
    #instruction=(
     #   """you are a agent that only answers questions related to time.
     #   based on a users given city you return the time"""
    #),
    #tools=[get_current_time],
    generate_content_config=types.GenerateContentConfig(
        response_modalities=['AUDIO'],  # Ensure the model knows to output audio
    ),
)
