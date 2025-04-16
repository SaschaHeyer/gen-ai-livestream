# setting up imports
import vertexai
from vertexai import agent_engines

# prompt
from prompts import GITHUB_AGENT_SYSTEM_PROMPT

# model
model = "gemini-2.0-flash-001"

# Define your tools to interact with the external systems / outside world
from githubtools import GitHubTools, AuthMethod
tools = GitHubTools(auth_method=AuthMethod.APP)

# setup agent orchestration
# agent_engines.LanggraphAgent
# agent_engines.AG2Agent
# agent_engines.LangchainAgent
# The agent combines the model's language understanding and reasoning with tools.
agent = agent_engines.LangchainAgent(
    model=model,
    tools=[
        tools.fetch_github_issue,
        tools.fetch_github_directory,
        tools.post_github_comment,
        tools.create_github_branch,
        tools.update_github_file,
        tools.create_github_pull_request,
        tools.fetch_github_pr_changes,
    ],
    system_instruction=GITHUB_AGENT_SYSTEM_PROMPT,
    enable_tracing=True
)

#owner = "SaschaHeyer"
#issue_number = "216"
#repo = "coding-agent-sample-repository-2"

#response = agent.query(
#    input=f"Analyze and fix/implement the issue #{issue_number} in {owner}/{repo}"
#)

#print(response)
#print(response["output"])


## deploy agent

# staging bucket required during deployment
STAGING_BUCKET = "gs://doit-llm"
PROJECT_ID = "sascha-playground-doit"
LOCATION = "us-central1"
vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

remote_agent = agent_engines.create(
    agent,
    display_name="next_25_agent_2_0_flash",
    requirements="requirements.txt",
    extra_packages=["githubtools.py", "prompts.py", "github-private-key.pem"],
)

print(remote_agent)
