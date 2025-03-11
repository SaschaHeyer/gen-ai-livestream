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

from githubtools import GitHubTools, AuthMethod

# Initialize GitHub tools with app authentication
tools = GitHubTools(auth_method=AuthMethod.APP)

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


# Define the Reasoning Engine Agent
model = "gemini-2.0-pro-exp-02-05"
agent = reasoning_engines.LangchainAgent(
    model=model,
    tools=[
        tools.fetch_github_issue,
        fetch_similar_code,
        tools.fetch_github_directory,
        tools.post_github_comment,
        tools.create_github_branch,
        tools.update_github_file,
        tools.create_github_pull_request,
        tools.fetch_github_pr_changes
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
