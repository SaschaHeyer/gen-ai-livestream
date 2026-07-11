# The ADK one-liner. Requires ADK from git main until the next PyPI release:
#   pip install "git+https://github.com/google/adk-python"
# The import path below is present on adk-python main and instantiates. It is NOT
# in released google-adk 2.4.0 yet, the announcement says "the next version".
from google.adk.agents import Agent
from google.adk.integrations.cloud_run import CloudRunSandboxCodeExecutor

analyst_agent = Agent(
    name="cloud_run_data_analyst",
    model="gemini-2.5-flash",
    instruction=(
        "You are a data analyst. Write and execute Python to answer questions "
        "about your data safely."
    ),
    code_executor=CloudRunSandboxCodeExecutor(),
)
