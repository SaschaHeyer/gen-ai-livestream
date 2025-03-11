import vertexai
from vertexai import agent_engines
from vertexai.preview import reasoning_engines

STAGING_BUCKET = "gs://doit-llm"
PROJECT_ID = "sascha-playground-doit"
LOCATION = "us-central1"
vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

from githubtools import GitHubTools, AuthMethod

tools = GitHubTools(auth_method=AuthMethod.APP)

model = "gemini-2.0-pro-exp-02-05"
#model = "gemini-2.0-flash-001"

agent = reasoning_engines.LangchainAgent(
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
    system_instruction="""
    You help developers to develop software by participating in GitHub issue discussions.

    You receive a GitHub issue and all current comments.

    use the tool `fetch_github_directory` to explore GitHub repositories before crafting a comment.
    The fetch_github_directory tool accepts an optional 'branch' parameter to fetch content from a specific branch.

    You participate in the discussion by:
    - helping users find answers to their questions
    - analyzing bug reports and proposing a fix when necessary
    - analyzing feature requests and proposing an implementation
    - being a sounding board in architecture discussions and proposing alternative solutions


    Agent, this is IMPORTANT:
    - DO NOT START WRITING YOUR RESPONSE UNTIL YOU HAVE COMPLETED THE ENTIRE EXPLORATION PHASE
    - VIEWING DIRECTORY LISTINGS IS NOT ENOUGH - YOU MUST EXAMINE FILE CONTENTS
    - ALWAYS USE A DEDICATED BRANCH. NOT THE MAIN BRANCH

    use the tool `fetch_github_pr_changes` to check if a potential suggested PR is already solving the issue
    - If there is already a PR in the comments (merge or not merged) do not create a new one your work is done

    use the tool `create_github_branch` to create a dedicated branch as preparation for the fix

    use the tool `update_github_file` to apply the fix in the new branch.
    The update_github_file tool can be used to:
    - Update existing files in a branch by specifying the file path, new content, commit message, and branch
    - Create new files in a branch by specifying a path to a file that doesn't exist yet

    use the tool `create_github_pull_request` to create a pull request.

    Always use the tool `post_github_comment` to post a response in markdown format explaining the code changes and referencing the PR.

    Always post a description of the fix as a comment to the initial issue using the post_github_comment tool.

    """,
)

#remote_agent = agent_engines.create(
    #agent,
    #requirements="requirements.txt",
    #extra_packages=["githubtools.py", "github-private-key.pem"],
#)


owner = "SaschaHeyer"
issue_number = "41"
repo = "coding-agent-sample-repository-2"

response = agent.query(
    input=f"Analyze and fix the issue #{issue_number} in {owner}/{repo}"
)


# print(remote_agent)

#import cloudpickle

#for tool in agent._tools:
    #try:
        #cloudpickle.dumps(tool)
        #print(f"✅ {tool.__name__} is serializable")
    #except Exception as e:
        #print(f"❌ {tool.__name__} is not serializable: {e}")


#owner = "SaschaHeyer"
#issue_number = "1"
#repo = "generative-ai-python-agent-test"

#print("agenttttt")
#response = agent.query(
    #input=f"Analyze and fix the issue #{issue_number} in {owner}/{repo}"
#)

##print(response)
#print(response["output"])

## console.print(f"[green]{response['output']}[/green]")

# Example usage
# issue_analysis = analyze_issue("SaschaHeyer", "coding-agent-sample-repository", 6)
# issue_analysis = analyze_issue("SaschaHeyer", "kubeip", 1)
# print(issue_analysis["output"])

# print(fetch_github_directory("deepset-ai", "haystack-core-integrations", "integrations"))

# directory_analysis = analyze_directory("deepset-ai", "haystack-core-integrations", "haystack-core-integrations/tree/main/integrations")
# print(directory_analysis)
