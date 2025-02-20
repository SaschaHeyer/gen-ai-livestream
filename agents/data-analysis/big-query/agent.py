import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    Tool,
    FunctionDeclaration,
)
from vertexai.preview import reasoning_engines
from google.cloud import bigquery, firestore
from langchain_google_firestore import FirestoreChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core import prompts
from langchain.agents.format_scratchpad.tools import format_to_tool_messages

# Vertex AI Configuration
PROJECT_ID = "sascha-playground-doit"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://doit-llm"

vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

# Initialize BigQuery Client
bq_client = bigquery.Client()

# 🔹 Firestore Chat History for Context
def get_session_history(session_id: str):
    client = firestore.Client(project=PROJECT_ID)
    return FirestoreChatMessageHistory(
        client=client,
        session_id=session_id,
        collection="history",
        encode_message=False,
    )

# 🔹 Function: List Datasets

def list_datasets_func() -> dict:
    """
    Get a list of datasets that will help answer the user's question
    """
    datasets = [dataset.dataset_id for dataset in bq_client.list_datasets()]
    return {"datasets": datasets}

# 🔹 Function: List Tables in a Dataset
def list_tables_func(dataset_id: str) -> dict:
    """List tables in a dataset that will help answer the user's question

    Args:
        dataset_id (str): Dataset ID to fetch tables from.
    """
    tables = [table.table_id for table in bq_client.list_tables(dataset_id)]
    return {"tables": tables}

# 🔹 Function: Get Table Schema & Metadata
def get_table_func(table_id: str) -> dict:
    """Get information about a table, including the description, schema, and number of rows that will help answer the user's question. Always use the fully qualified dataset and table names.

    Args:
        table_id (str): Fully qualified ID of the table to get information about
    """
    table = bq_client.get_table(table_id)
    return {
        "description": table.description or "No description available",
        "schema": [field.name for field in table.schema],
        "num_rows": table.num_rows,
    }

# 🔹 Function: Execute SQL Query
def sql_query_func(query: str) -> dict:
    """Get information from data in BigQuery using SQL queries

    Args:
        query (str):SQL query on a single line that will help give quantitative answers to the user's question when run on a BigQuery dataset and table. In the SQL query, always use the fully qualified dataset and table names..
    """
    job_config = bigquery.QueryJobConfig(maximum_bytes_billed=100000000)  # 100MB limit

    try:
        query_job = bq_client.query(query, job_config=job_config)
        results = [dict(row) for row in query_job.result()]
        return {"results": results}
    except Exception as e:
        return {"error": str(e)}


# 🔹 System Prompt for Agent
system_prompt = """
Please give a concise, high-level summary followed by detail in
            plain language about where the information in your response is
            coming from in the database. Only use information that you learn
            from BigQuery, do not make up information.
"""

# 🔹 Define Chat Prompt Template
chat_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        #MessagesPlaceholder(variable_name="history"),
        ("user", "{input}"),
    ]
)

custom_prompt_template = {
    "user_input": lambda x: x["input"],
    "history": lambda x: x["history"],
    "agent_scratchpad": lambda x: format_to_tool_messages(x["intermediate_steps"]),
} | ChatPromptTemplate.from_messages([
    ("placeholder", "{history}"),
    ("user", "{user_input}"),
    ("placeholder", "{agent_scratchpad}"),
])




# 🔹 Define Agent with Reasoning Engine
agent = reasoning_engines.LangchainAgent(
    #prompt=chat_prompt,
    #system_instruction=system_prompt,
    #prompt=custom_prompt_template,
    model_kwargs={"temperature": 0},
    model="gemini-1.5-pro",
    #chat_history=get_session_history,
    tools=[list_datasets_func,
        list_tables_func,
       get_table_func,
        sql_query_func],
        agent_executor_kwargs={"return_intermediate_steps": True},
)

# 🔹 Deploy Agent as a Remote Reasoning Engine
#remote_agent = reasoning_engines.ReasoningEngine.create(
#    agent,
#    requirements=[
#        "google-cloud-aiplatform[langchain,reasoningengine]",
#        "langchain-google-firestore",
#    ],
#)

remote_agent = agent

#response = remote_agent.query(
#    input="What datasets are available in BigQuery?",
#)


#print(response["output"])

#response = remote_agent.query(
#    input="What tables exist in the dataset 'thelook_ecommerce'?",
#)
#print(response["output"])

#response = remote_agent.query(
#    input="What are the columns in 'thelook_ecommerce.orders'?",
#)
#print(response["output"])

response = remote_agent.query(
    input="Which product categories have the highest profit margins? Calculate it"
)
#print(response)
print(response["output"])
