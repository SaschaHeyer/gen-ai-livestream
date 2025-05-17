import asyncio
import time
import json
import os
import requests
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from dotenv import load_dotenv
from google.adk.tools import LongRunningFunctionTool

load_dotenv()

# Set the URL of your Flask app
FLASK_APP_URL = os.environ.get('FLASK_APP_URL', 'http://127.0.0.1:5000')

# 1. Define the long-running function with human escalation
def human_escalation(question: str) -> dict:
    """
    Escalates a question to a human operator and waits for their response.

    Args:
      question: The question or issue that needs human input.

    Returns:
      A final status dictionary with the human's response.
    """
    progress_updates = []

    # Initial update
    progress_updates.append({
        "status": "pending",
        "message": f"Escalating to a human: '{question}'"
    })

    # Make API call to escalate to human
    try:
        print(f"Attempting to connect to Flask app at: {FLASK_APP_URL}")

        try:
            response = requests.post(
                f"{FLASK_APP_URL}/escalate",
                json={"question": question},
                headers={"Content-Type": "application/json"},
                timeout=10  # Add timeout to prevent hanging
            )

            if response.status_code != 200:
                return {
                    "status": "error",
                    "message": f"Failed to escalate (Status {response.status_code}): {response.text}",
                    "updates": progress_updates
                }
        except requests.exceptions.RequestException as req_err:
            return {
                "status": "error",
                "message": f"Connection error: {str(req_err)}. Make sure the Flask app is running at {FLASK_APP_URL}",
                "updates": progress_updates
            }

        data = response.json()
        conversation_id = data.get('conversation_id')

        # Add escalation confirmation
        progress_updates.append({
            "status": "pending",
            "message": "Successfully escalated to human operator. Waiting for response...",
            "conversation_id": conversation_id
        })

        # Poll for human response (up to 5 minutes)
        max_attempts = 30  # 5 minutes with 10-second intervals
        for attempt in range(max_attempts):
            # Wait 10 seconds between checks
            time.sleep(10)

            # Check if human has responded
            check_response = requests.get(f"{FLASK_APP_URL}/check/{conversation_id}")

            if check_response.status_code != 200:
                progress_updates.append({
                    "status": "error",
                    "message": f"Error checking response status: {check_response.text}"
                })
                continue

            check_data = check_response.json()

            # Add progress update
            progress_updates.append({
                "status": "pending",
                "progress": f"Waiting for human response... ({attempt + 1}/{max_attempts})",
                "estimated_completion_time": f"~{(max_attempts - (attempt + 1)) * 10} seconds remaining (max)"
            })

            # If human has responded, return their response
            if check_data.get('status') == 'completed' and check_data.get('response'):
                return {
                    "status": "completed",
                    "result": check_data['response'],
                    "updates": progress_updates
                }

        # If we've reached here, we timed out waiting for a response
        return {
            "status": "timeout",
            "message": "Timed out waiting for human response. Please try again later.",
            "updates": progress_updates
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error during human escalation: {str(e)}",
            "updates": progress_updates
        }

# 2. Wrap the function with LongRunningFunctionTool
escalation_tool = LongRunningFunctionTool(func=human_escalation)

# 3. Use the tool in an Agent
escalation_agent = Agent(
    model="gemini-2.0-flash",
    name='escalation_agent',
    instruction="""You are an agent that can escalate questions to a human when needed.
    If the user asks a complex question or needs help that requires human expertise,
    use the 'human_escalation' tool to hand off the question to a human operator.

    Keep the user informed about the escalation process based on the tool's updates.
    Only provide the final human response when the tool indicates completion.

    Always ask the user if they'd like to escalate to a human if they seem stuck or frustrated.
    Let them know that a human will respond as soon as possible, and the response
    might take a few minutes.""",
    tools=[escalation_tool]
)

root_agent = escalation_agent

if __name__ == "__main__":
    APP_NAME = "human_escalation"
    USER_ID = "1234"
    SESSION_ID = "session1234"

    # Session and Runner
    session_service = InMemorySessionService()
    session = session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    runner = Runner(agent=escalation_agent, app_name=APP_NAME, session_service=session_service)

    # Agent Interaction
    async def call_agent(query):
        content = types.Content(role='user', parts=[types.Part(text=query)])
        events_async = runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=content)

        async for event in events_async:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_call:
                        # Handle function call and progress update
                        function_call = part.function_call
                        print(f"Function Call: {function_call}")
                        # The agent will pause and wait for progress or final response
                    elif part.function_response:
                        # Handle function response after processing
                        function_response = part.function_response
                        print(f"Function Response: {function_response}")
                        if function_response.response:
                            print("Final Response:", function_response.response)
                    elif part.text:
                        # Regular text response from the agent
                        print(f"Agent: {part.text}")

    # Call the agent with a sample query
    asyncio.run(call_agent("I need to speak with a human about a complex issue please"))
