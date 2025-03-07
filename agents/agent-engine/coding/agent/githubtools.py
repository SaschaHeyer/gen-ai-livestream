import requests
import os
import base64

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console

console = Console()


class GitHubTools:
    def __init__(self):
        self.token = os.environ.get("GITHUB_TOKEN")

    def fetch_github_issue(self, owner: str, repo: str, issue_number: int):
        """
        Fetches the description and comments of a specific GitHub issue.
        """
        console.print("[cyan]USE TOOL FETCH_ISSUE[/cyan]")

        headers = {"Authorization": f"Bearer {self.token}"}

        # Fetch issue details
        issue_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
        issue_response = requests.get(issue_url, headers=headers)
        if issue_response.status_code != 200:
            return {"error": f"Failed to fetch issue: {issue_response.text}"}
        issue_data = issue_response.json()

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

        headers = {"Authorization": f"Bearer {self.token}"}

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

        headers = {"Authorization": f"Bearer {self.token}"}

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
        # print(f"USE TOOL UPDATE_FILE on branch {branch}")

        if branch in {"main", "master"}:
            return {
                "error": f"direct commits to master or main branch are not allowed use a dedicated branch instead"
            }

        headers = {"Authorization": f"Bearer {self.token}"}

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

        headers = {"Authorization": f"Bearer {self.token}"}

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
            github_token (str): GitHub personal access token.

        Returns:
            dict: Contains a list of changed files and the corresponding diffs.
        """
        # print(f"USE TOOL FETCH_PR_CHANGES for PR #{pr_number}")
        console.print(f"[cyan]USE TOOL FETCH_PR_CHANGES for PR #{pr_number}[/cyan]")

        headers = {"Authorization": f"Bearer {self.token}"}

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

        headers = {"Authorization": f"Bearer {self.token}"}

        data = {"body": comment}
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 201:
            print(f"error: {response.text}")
            return {"error": f"Failed to post comment: {response.text}"}
        return response.json()
