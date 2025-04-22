from google.adk.sessions import InMemorySessionService
from google.adk.sessions import Session
from google.adk.sessions import VertexAiSessionService

PROJECT_ID = "sascha-playground-doit"
LOCATION = "us-central1"

service = VertexAiSessionService(project=PROJECT_ID, location=LOCATION)

# Create a simple session to examine its properties
#service = InMemorySessionService()

example_session: Session = service.create_session(
    app_name="projects/234439745674/locations/us-central1/reasoningEngines/7069393573669502976",
    user_id="sascha",
    state={"initial_key": "initial_value"} # State can be initialized
)

print(f"--- Examining Session Properties ---")
print(f"ID (`id`):                {example_session.id}")
print(f"Application Name (`app_name`): {example_session.app_name}")
print(f"User ID (`user_id`):         {example_session.user_id}")
print(f"State (`state`):           {example_session.state}") # Note: Only shows initial state here
print(f"Events (`events`):         {example_session.events}") # Initially empty
print(f"Last Update (`last_update_time`): {example_session.last_update_time:.2f}")
print(f"---------------------------------")

# Clean up (optional for this example)
#service.delete_session(app_name=example_session.app_name,
#                            user_id=example_session.user_id,
#                            session_id=example_session.id)
