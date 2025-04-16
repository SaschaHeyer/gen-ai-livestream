import logging
import warnings
from google.adk import Agent
from .config import Config
from .prompts import INSTRUCTION

# Define your tools to interact with the external systems / outside world
from .tools.tools import GitHubTools, AuthMethod
github_tools = GitHubTools(auth_method=AuthMethod.APP)

warnings.filterwarnings("ignore", category=UserWarning, module=".*pydantic.*")

configs = Config()

# configure logging __name__
logger = logging.getLogger(__name__)

root_agent = Agent(
    model=configs.agent_settings.model,
    instruction=INSTRUCTION,
    name=configs.agent_settings.name,
    tools=[
        github_tools.fetch_github_issue,
        github_tools.fetch_github_directory,
        github_tools.post_github_comment,
        github_tools.create_github_branch,
        github_tools.update_github_file,
        github_tools.create_github_pull_request,
        github_tools.fetch_github_pr_changes,
    ],
)
