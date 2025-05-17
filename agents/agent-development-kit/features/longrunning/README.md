# ADK Agent with Human Escalation

This project implements a Google ADK agent with human escalation capabilities using a Flask web application. It allows an agent to hand off complex questions to human operators and then resume the conversation once a human has provided input.

## Project Structure

- `app.py` - Flask web application for human operators to respond to escalated questions
- `agent_with_escalation.py` - ADK agent with human escalation functionality
- `templates/` - HTML templates for the web interface
  - `dashboard.html` - Dashboard for human operators to see all escalated conversations
  - `respond.html` - Interface for human operators to respond to specific questions
  - `error.html` - Error page template

## Prerequisites

- Python 3.8+
- Google ADK
- Flask
- An accessible URL for the Flask app (to be used by the agent)

## Setup Instructions

1. Install the required dependencies:

```bash
pip install google-adk flask requests python-dotenv
```

2. Set up environment variables:

Create a `.env` file in the project root with the following variables:

```
# Google ADK Authentication
GOOGLE_API_KEY=your_google_api_key

# Flask App Configuration
FLASK_SECRET_KEY=your_secret_key_for_flask_session
FLASK_APP_URL=http://localhost:5000  # Change if deploying elsewhere
```

3. Start the Flask web application:

```bash
# Start in one terminal
python -m flask --app app run
```

4. Run the agent in another terminal:

```bash
# Run the agent in a separate terminal
python agent_with_escalation.py
```

## How it Works

1. **Agent Interaction:**
   - When a user interacts with the ADK agent and needs human assistance, the agent calls the `human_escalation` function.
   - This function makes an API call to the Flask app to escalate the question to a human operator.

2. **Human Interface:**
   - Human operators can visit the dashboard at http://localhost:5000 to see all escalated questions.
   - They can click on a question to provide a response through the web interface.

3. **Response Handling:**
   - The agent periodically polls the Flask app to check if a human has responded.
   - Once a response is received, it's relayed back to the user through the agent.

## Deployment Options

### Local Development

For local development, both the agent and Flask app can run on the same machine.

### Production Deployment

For production:

1. Deploy the Flask app to a cloud service like Google Cloud Run or Heroku.
2. Update the `FLASK_APP_URL` environment variable to point to the deployed URL.
3. Deploy the agent to your preferred environment.

## Customizing the Agent

You can customize the agent's behavior by modifying the instruction in `agent_with_escalation.py`:

```python
escalation_agent = Agent(
    model="gemini-2.0-flash",
    name='escalation_agent',
    instruction="""Your custom instructions here...""",
    tools=[escalation_tool]
)
```

## Customizing the Web Interface

The HTML templates can be customized to match your branding and requirements by modifying the files in the `templates/` directory.

## Timeout Configuration

By default, the agent will wait up to 5 minutes for a human response. You can adjust this by modifying the `max_attempts` variable in the `human_escalation` function in `agent_with_escalation.py`.