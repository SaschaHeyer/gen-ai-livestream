# setting up the environment
import vertexai
from vertexai import agent_engines

# staging bucket required during deployment
STAGING_BUCKET = "gs://doit-llm"
PROJECT_ID = "sascha-playground-doit"
LOCATION = "us-central1"
vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

# Define your tools to interact with the external systems / outside world
from githubtools import GitHubTools, AuthMethod
tools = GitHubTools(auth_method=AuthMethod.APP)

# prompt
from prompts import GITHUB_AGENT_SYSTEM_PROMPT, GITHUB_AGENT_SYSTEM_PROMPT_MINIMAL

# model
#model = "gemini-2.0-pro-exp-02-05"
model = "gemini-2.0-flash-001"

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
    agent_executor_kwargs={"return_intermediate_steps": True, "max_iterations": 50},
    system_instruction=GITHUB_AGENT_SYSTEM_PROMPT,
    enable_tracing=True
)


#import cloudpickle
#for tool in agent._tools:
    #try:
        #cloudpickle.dumps(tool)
        #print(f"✅ {tool.__name__} is serializable")
    #except Exception as e:
        #print(f"❌ {tool.__name__} is not serializable: {e}")

owner = "SaschaHeyer"
issue_number = "3"
repo = "agent-sample-5"

agent.query( input=f"Analyze and fix/implement the issue #{issue_number} in {owner}/{repo}")

response = agent.query(
    input=f"Analyze and fix/implement the issue #{issue_number} in {owner}/{repo}"
)

#print(response)
print(response["output"])


## deploy agent
#remote_agent = agent_engines.create(
    #agent,
    #display_name="githhub_agent",
    #requirements="requirements.txt",
    #extra_packages=["githubtools.py", "prompts.py", "github-private-key.pem"],
#)

#print(remote_agent)
