import requests
import os
import vertexai
from vertexai.preview import reasoning_engines

import base64

STAGING_BUCKET = "gs://doit-llm"
PROJECT_ID = "sascha-playground-doit"
LOCATION = "us-central1"

from rich.console import Console
console = Console()

from dotenv import load_dotenv
load_dotenv()

vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

#vector
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

# Firestore Client
firestore_client = firestore.Client()
collection = firestore_client.collection("code-embeddings")

# Initialize Vertex AI Embedding Model
MODEL_NAME = "text-embedding-005"
DIMENSIONALITY = 256
embedding_model = TextEmbeddingModel.from_pretrained(MODEL_NAME)


def fetch_similar_code(query: str, limit: int = 5):
    """
    Fetches similar code snippets from Firestore using vector search.

    Args:
        query (str): The natural language query (e.g., "Find a function that adds two numbers").
        limit (int): Number of similar code snippets to return.

    Returns:
        list: List of dictionaries containing file paths and relevant code snippets.
    """
    print(f"🔍 Searching Firestore for relevant code snippets: {query}")

    # Generate an embedding for the query
    try:
        inputs = [TextEmbeddingInput(query, "CODE_RETRIEVAL_QUERY")]
        embeddings = embedding_model.get_embeddings(inputs, output_dimensionality=DIMENSIONALITY)
        query_embedding = embeddings[0].values
    except Exception as e:
        print(f"❌ Embedding generation failed: {str(e)}")
        return []

    # Perform vector search in Firestore
    vector_query = collection.find_nearest(
        vector_field="embedding",
        query_vector=Vector(query_embedding),
        distance_measure=DistanceMeasure.EUCLIDEAN,  # Lower = more similar
        limit=limit,
        distance_result_field="vector_distance",  # Store similarity score
    )

    results = []
    for doc in vector_query.stream():
        result = doc.to_dict()
        similarity_score = doc.get("vector_distance")

        results.append({
            "file_path": result.get("file_path"),
            "content": result.get("content"),
            "similarity_score": similarity_score
        })

    print(f"✅ Retrieved {len(results)} relevant code snippets.")
    return results


def fetch_github_issue(owner: str, repo: str, issue_number: int):
    """
    Fetches the description and comments of a specific GitHub issue.
    """
    console.print("[cyan]USE TOOL FETCH_ISSUE[/cyan]")

    headers = {"Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN')}"}

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

def _process_file_content(content: str, encoding: str) -> str:
    """Process file content based on encoding"""
    if encoding == "base64":
        return base64.b64decode(content).decode("utf-8")
    return content

def fetch_github_directory(owner: str, repo: str, path: str, branch: str = "main"):
    """
    Navigates and fetches content from GitHub repositories.
    
    Args:
        owner (str): GitHub repository owner.
        repo (str): Repository name.
        path (str): Path within the repository to fetch.
        branch (str): The branch to fetch from (defaults to "main").

    Returns:
        dict: Content of the directory or file.
    """
    console.print("[cyan]USE TOOL FETCH_DIRECTORY[/cyan]")
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    console.print(f"[cyan]Fetching from {url}[/cyan]")

    headers = {"Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN')}"}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return {"error": f"Failed to fetch directory contents: {response.text}"}

    contents = response.json()

    # single file
    if not isinstance(contents, list):
        console.print("[cyan]Processing single file[/cyan]")

        content = {
            "name": contents["name"],
            "content": _process_file_content(contents["content"], contents["encoding"]),
        }
        
        return content

    return response.json()

def create_github_branch(owner: str, repo: str, new_branch: str):
    """
    Creates a new branch in a GitHub repository

    Args:
        owner (str): GitHub repository owner.
        repo (str): Repository name.
        new_branch (str): The name of the new branch to create.

    Returns:
        dict: API response or error message.
    """
    #print("USE TOOL CREATE_BRANCH")
    console.print("[cyan]USE TOOL CREATE_BRANCH[/cyan]")

    headers = {"Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN')}"}

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
    owner: str,
    repo: str,
    file_path: str,
    new_content: str,
    commit_message: str,
    branch: str,
):
    """
    Updates a file in a GitHub repository by modifying its content and committing the change
    to a specific branch. If the file doesn't exist, it will be created.

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
    #print(f"USE TOOL UPDATE_FILE on branch {branch}")

    if branch in {"main", "master"}:
        return {"error": f"direct commits to master or main branch are not allowed use a dedicated branch instead"}

    headers = {"Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN')}"}

    # Fetch the current file to get its SHA
    file_url = (
        f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={branch}"
    )
    response = requests.get(file_url, headers=headers)

    # Encode the new content to Base64
    encoded_content = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")

    # Create the request payload
    payload = {
        "message": commit_message,
        "content": encoded_content,
        "branch": branch,
    }

    # If the file exists, add its SHA to the payload
    if response.status_code == 200:
        file_data = response.json()
        payload["sha"] = file_data["sha"]  # Required for updating the file
    elif response.status_code != 404:
        # If it's not a 404 (file not found), then there's a different error
        return {"error": f"Failed to fetch file: {response.text}"}
    # For 404, we're creating a new file so we don't need a SHA

    # Send the request to update or create the file
    update_response = requests.put(file_url, headers=headers, json=payload)

    if update_response.status_code not in [200, 201]:
        return {"error": f"Failed to update/create file: {update_response.text}"}

    return update_response.json()

def create_github_pull_request(
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
    #print(f"USE TOOL CREATE_PULL_REQUEST for issue #{issue_number}")
    console.print(f"[cyan]USE TOOL CREATE_PULL_REQUEST for issue #{issue_number}[/cyan]")

    headers = {"Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN')}"}

    # Automatically link the PR to the issue
    body += f"\n\nCloses #{issue_number}"

    # Create the pull request payload
    payload = {"title": title, "body": body, "head": branch, "base": base_branch}

    pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    response = requests.post(pr_url, headers=headers, json=payload)

    if response.status_code not in [200, 201]:
        return {"error": f"Failed to create pull request: {response.text}"}

    return response.json()

def fetch_github_pr_changes(owner: str, repo: str, pr_number: int):
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
    #print(f"USE TOOL FETCH_PR_CHANGES for PR #{pr_number}")
    console.print(f"[cyan]USE TOOL FETCH_PR_CHANGES for PR #{pr_number}[/cyan]")

    headers = {"Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN')}"}

    # Fetch list of changed files in the PR
    pr_files_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    response = requests.get(pr_files_url, headers=headers)

    if response.status_code != 200:
        return {"error": f"Failed to fetch PR changes: {response.text}"}

    files_changed = response.json()

    changes = []
    for file in files_changed:
        filename = file["filename"]
        patch = file.get("patch", "No diff available")

        changes.append({
            "filename": filename,
            "diff": patch
        })

    return {"pr_number": pr_number, "changes": changes}

def post_github_comment(owner: str, repo: str, issue_number: int, comment: str):
    """
    Posts a comment to a specific GitHub issue.
    """
    #print("USE TOOL POST_COMMENT")
    console.print(f"[cyan]USE TOOL POST_COMMENT[/cyan]")
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"

    headers = {"Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN')}"}

    data = {"body": comment}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 201:
        print(f"error: {response.text}")
        return {"error": f"Failed to post comment: {response.text}"}
    return response.json()


# Define the Reasoning Engine Agent
model = "gemini-2.0-pro-exp-02-05"
agent = reasoning_engines.LangchainAgent(
    model=model,
    tools=[
        fetch_github_issue,
        fetch_similar_code,
        post_github_comment,
        create_github_branch,
        update_github_file,
        create_github_pull_request,
        fetch_github_pr_changes
    ],
    agent_executor_kwargs={"return_intermediate_steps": True, "max_iterations": 50},
    system_instruction="""
    You help developers to develop software by participating in GitHub issue discussions.

    You receive a GitHub issue and all current comments.

    use the tool `fetch_similar_code` to find matching GitHub files based on a query that is transformed to an embedding
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
    
    Use the tool `post_github_comment` to post a response in markdown format explaining the code changes and referencing the PR.

    The post_github_comment tool should use markdown and include a description of the fix provided with the PR.

    """,
)

#remote_agent = reasoning_engines.ReasoningEngine.create(
    #agent,
    #requirements=["google-cloud-aiplatform[langchain,reasoningengine]"],
#)


#print(remote_agent)

owner = "SaschaHeyer"
issue_number = "10"
repo = "coding-agent-sample-repository-2"

response = agent.query(
        input=f"Analyze and fix the issue #{issue_number} in {owner}/{repo}"
    )

#print(response)
#print(response["output"])

console.print(f"[green]{response['output']}[/green]")

# Example usage
# issue_analysis = analyze_issue("SaschaHeyer", "coding-agent-sample-repository", 6)
# issue_analysis = analyze_issue("SaschaHeyer", "kubeip", 1)
# print(issue_analysis["output"])

# print(fetch_github_directory("deepset-ai", "haystack-core-integrations", "integrations"))

# directory_analysis = analyze_directory("deepset-ai", "haystack-core-integrations", "haystack-core-integrations/tree/main/integrations")
# print(directory_analysis)
