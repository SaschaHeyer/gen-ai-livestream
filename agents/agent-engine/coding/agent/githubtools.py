import requests
import os
import base64
import time
import jwt
import enum
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console

console = Console()


class AuthMethod(enum.Enum):
    """Authentication methods for GitHub API."""
    TOKEN = "token"
    APP = "app"


class GitHubTools:
    def __init__(self, auth_method: AuthMethod = AuthMethod.TOKEN, installation_id: Optional[int] = None):
        """
        Initialize GitHub tools with specified authentication method.

        Args:
            auth_method (AuthMethod): Authentication method to use.
                                      Options: AuthMethod.TOKEN (Personal Access Token) or AuthMethod.APP (GitHub App)
            installation_id (Optional[int]): The installation ID for GitHub App installations
        """
        self.auth_method = auth_method
        self.installation_id = installation_id
        self.installation_token = None

        if auth_method == AuthMethod.TOKEN:
            self.token = os.environ.get("GITHUB_TOKEN")
            if not self.token:
                console.print("[red]Error: GITHUB_TOKEN environment variable not set[/red]")
        elif auth_method == AuthMethod.APP:
            self.app_id = os.environ.get("GITHUB_APP_ID")
            self.private_key_path = os.environ.get("GITHUB_PRIVATE_KEY_PATH")

            if not self.app_id or not self.private_key_path:
                console.print("[red]Error: GITHUB_APP_ID or GITHUB_PRIVATE_KEY_PATH environment variable not set[/red]")

            # Generate JWT token for GitHub App authentication
            self.token = self._get_jwt_token()

            # If installation_id is provided, get an installation token
            if installation_id:
                self.installation_token = self._get_installation_token(installation_id)
                if self.installation_token:
                    console.print("[green]Installation token generated successfully[/green]")
                else:
                    console.print("[red]Failed to get installation token[/red]")
        else:
            self.token = os.environ.get("GITHUB_TOKEN")
            console.print(f"[yellow]Warning: Unknown auth method '{auth_method}', defaulting to token[/yellow]")

    def _get_jwt_token(self):
        """
        Generate a JWT token for GitHub App authentication.

        Returns:
            str: JWT token for GitHub App authentication
        """
        try:
            # Get the absolute path to the private key
            import os
            abs_key_path = os.path.abspath(self.private_key_path)
            console.print(f"[cyan]Using private key at: {abs_key_path}[/cyan]")

            # Read the private key
            with open(abs_key_path, 'r') as key_file:
                private_key = key_file.read()

            # Create JWT payload
            now = int(time.time())
            payload = {
                "iat": now,                  # Issued at time
                "exp": now + (10 * 60),      # JWT expires in 10 minutes
                "iss": self.app_id           # GitHub App ID
            }

            console.print(f"[cyan]Creating JWT with app_id: {self.app_id}[/cyan]")

            # Create JWT token
            token = jwt.encode(payload, private_key, algorithm="RS256")

            # If token is returned as bytes (depends on jwt version), decode to string
            if isinstance(token, bytes):
                token = token.decode('utf-8')

            console.print("[green]JWT token generated successfully[/green]")
            return token
        except Exception as e:
            console.print(f"[red]Error generating JWT token: {str(e)}[/red]")
            return None

    def _get_installation_token(self, installation_id: int):
        """
        Generate an installation access token for a GitHub App installation.

        Args:
            installation_id (int): The ID of the installation.

        Returns:
            str: Installation access token or None if failed
        """
        try:
            # We need a JWT token to request an installation token
            if not self.token:
                console.print("[red]Error: JWT token is required to get an installation token[/red]")
                return None

            # Get the installation token
            url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
            headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github.v3+json"}

            console.print(f"[cyan]Requesting installation token for installation ID: {installation_id}[/cyan]")
            response = requests.post(url, headers=headers)

            if response.status_code != 201:
                console.print(f"[red]Error getting installation token: {response.status_code} - {response.text}[/red]")
                return None

            token_data = response.json()
            return token_data.get("token")

        except Exception as e:
            console.print(f"[red]Error generating installation token: {str(e)}[/red]")
            return None

    def _get_auth_headers(self):
        """
        Get authorization headers based on authentication method.

        Returns:
            dict: Headers with authorization information
        """
        if self.auth_method == AuthMethod.APP:
            # If we have an installation token, use it (preferred for API operations)
            if self.installation_token:
                return {"Authorization": f"token {self.installation_token}", "Accept": "application/vnd.github.v3+json"}

            # Fall back to JWT token if no installation token
            if not self.token:
                console.print("[red]Error: JWT token for GitHub App is None[/red]")
                # Fallback to token auth if JWT token generation failed
                return {"Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN')}", "Accept": "application/vnd.github.v3+json"}

            # GitHub App authentication uses Bearer prefix for JWT
            return {"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github.v3+json"}
        else:  # token auth is default
            return {"Authorization": f"token {self.token}", "Accept": "application/vnd.github.v3+json"}

    def fetch_github_issue(self, owner: str, repo: str, issue_number: int):
        """
        Fetches the description and comments of a specific GitHub issue.
        """
        console.print("[cyan]USE TOOL FETCH_ISSUE[/cyan]")

        headers = self._get_auth_headers()

        # Fetch issue details
        issue_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
        issue_response = requests.get(issue_url, headers=headers)
        print(issue_response)
        if issue_response.status_code != 200:
            return {"error": f"Failed to fetch issue: {issue_response.text}"}
        issue_data = issue_response.json()
        print(issue_data)

        # Fetch issue comments
        comments_url = issue_data.get("comments_url")
        comments_response = requests.get(comments_url, headers=headers)
        comments = []
        if comments_response.status_code == 200:
            comments = [comment["body"] for comment in comments_response.json()]

        return {
            "title": issue_data.get("title"),
            "description": issue_data.get("body"),
            "comments": comments,
        }

    def _process_file_content(self, content: str, encoding: str) -> str:
        """Process file content based on encoding"""
        if encoding == "base64":
            return base64.b64decode(content).decode("utf-8")
        return content

    def fetch_github_directory(self, owner: str, repo: str, path: str):
        """
        Navigates and fetches content from GitHub repositories.
        """
        console.print("[cyan]USE TOOL FETCH_DIRECTORY[/cyan]")
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        print(url)

        headers = self._get_auth_headers()

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return {"error": f"Failed to fetch directory contents: {response.text}"}

        contents = response.json()

        # single file
        if not isinstance(contents, list):

            print("PROCESS SINGLE FILE")

            content = {
                "name": contents["name"],
                "content": self._process_file_content(
                    contents["content"], contents["encoding"]
                ),
            }
            print(content)

            return content

        return response.json()

    def create_github_branch(self, owner: str, repo: str, new_branch: str):
        """
        Creates a new branch in a GitHub repository

        Args:
            owner (str): GitHub repository owner.
            repo (str): Repository name.
            new_branch (str): The name of the new branch to create.

        Returns:
            dict: API response or error message.
        """
        # print("USE TOOL CREATE_BRANCH")
        console.print("[cyan]USE TOOL CREATE_BRANCH[/cyan]")

        headers = self._get_auth_headers()

        # Fetch the latest commit SHA of the base branch
        branch_url = f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/main"
        response = requests.get(branch_url, headers=headers)

        if response.status_code != 200:
            return {"error": f"Failed to fetch base branch: {response.text}"}

        base_sha = response.json()["object"]["sha"]  # Get the latest commit SHA

        # Create the new branch reference
        new_branch_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
        payload = {"ref": f"refs/heads/{new_branch}", "sha": base_sha}

        response = requests.post(new_branch_url, headers=headers, json=payload)

        if response.status_code != 201:
            return {"error": f"Failed to create branch: {response.text}"}

        return {"message": f"Branch '{new_branch}' created successfully."}

    def update_github_file(
        self,
        owner: str,
        repo: str,
        file_path: str,
        new_content: str,
        commit_message: str,
        branch: str,
    ):
        """
        Updates a file in a GitHub repository by modifying its content and committing the change
        to a specific branch.

        Args:
            owner (str): GitHub repository owner.
            repo (str): Repository name.
            file_path (str): Path to the file in the repository.
            new_content (str): New content to be written into the file.
            commit_message (str): Commit message for the update.
            branch (str): The branch where the changes will be pushed.

        Returns:
            dict: API response or error message.
        """
        console.print(f"[cyan]USE TOOL UPDATE_FILE on branch {branch}[/cyan]")

        if branch in {"main", "master"}:
            return {
                "error": f"direct commits to master or main branch are not allowed use a dedicated branch instead"
            }

        headers = self._get_auth_headers()

        # Fetch the current file to get its SHA
        file_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={branch}"
        response = requests.get(file_url, headers=headers)

        if response.status_code != 200:
            return {"error": f"Failed to fetch file: {response.text}"}

        file_data = response.json()
        sha = file_data["sha"]  # Required for updating the file

        # Encode the new content to Base64
        encoded_content = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")

        # Create the request payload
        payload = {
            "message": commit_message,
            "content": encoded_content,
            "sha": sha,
            "branch": branch,
        }

        # Send the request to update the file
        update_response = requests.put(file_url, headers=headers, json=payload)

        if update_response.status_code not in [200, 201]:
            return {"error": f"Failed to update file: {update_response.text}"}

        return update_response.json()

    def create_github_pull_request(
        self,
        owner: str,
        repo: str,
        branch: str,
        base_branch: str,
        issue_number: int,
        title: str,
        body: str,
    ):
        """
        Creates a pull request to merge changes from the new branch into the base branch and links it to an issue.

        Args:
            owner (str): GitHub repository owner.
            repo (str): Repository name.
            branch (str): The feature branch containing the changes.
            base_branch (str): The target branch (usually "main").
            issue_number (int): The GitHub issue number this PR addresses.
            title (str): Title of the pull request.
            body (str): Description of the pull request.

        Returns:
            dict: API response or error message.
        """
        # print(f"USE TOOL CREATE_PULL_REQUEST for issue #{issue_number}")
        console.print(
            f"[cyan]USE TOOL CREATE_PULL_REQUEST for issue #{issue_number}[/cyan]"
        )

        headers = self._get_auth_headers()

        # Automatically link the PR to the issue
        body += f"\n\nCloses #{issue_number}"

        # Create the pull request payload
        payload = {"title": title, "body": body, "head": branch, "base": base_branch}

        pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        response = requests.post(pr_url, headers=headers, json=payload)

        if response.status_code not in [200, 201]:
            return {"error": f"Failed to create pull request: {response.text}"}

        return response.json()

    def fetch_github_pr_changes(self, owner: str, repo: str, pr_number: int):
        """
        Fetches the list of files changed and their diffs in a GitHub pull request.

        Args:
            owner (str): GitHub repository owner.
            repo (str): Repository name.
            pr_number (int): The pull request number.

        Returns:
            dict: Contains a list of changed files and the corresponding diffs.
        """
        # print(f"USE TOOL FETCH_PR_CHANGES for PR #{pr_number}")
        console.print(f"[cyan]USE TOOL FETCH_PR_CHANGES for PR #{pr_number}[/cyan]")

        headers = self._get_auth_headers()

        # Fetch list of changed files in the PR
        pr_files_url = (
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
        )
        response = requests.get(pr_files_url, headers=headers)

        if response.status_code != 200:
            return {"error": f"Failed to fetch PR changes: {response.text}"}

        files_changed = response.json()

        changes = []
        for file in files_changed:
            filename = file["filename"]
            patch = file.get("patch", "No diff available")

            changes.append({"filename": filename, "diff": patch})

        return {"pr_number": pr_number, "changes": changes}

    def post_github_comment(
        self, owner: str, repo: str, issue_number: int, comment: str
    ):
        """
        Posts a comment to a specific GitHub issue.
        """
        # print("USE TOOL POST_COMMENT")
        console.print(f"[cyan]USE TOOL POST_COMMENT[/cyan]")
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"

        headers = self._get_auth_headers()

        data = {"body": comment}
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 201:
            print(f"error: {response.text}")
            return {"error": f"Failed to post comment: {response.text}"}
        return response.json()
