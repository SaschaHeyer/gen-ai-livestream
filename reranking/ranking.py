from google.cloud import discoveryengine_v1alpha as discoveryengine

# Replace with your project ID
project_id = "sascha-playground-doit"

# Initialize the Ranking API client
client = discoveryengine.RankServiceClient()

# Define the full resource name of the ranking config
ranking_config = client.ranking_config_path(
    project=project_id,
    location="global",
    ranking_config="default_ranking_config",
)

# Define the example query
query = "Which language can I use for web development?"

# Define the potential answers as records
records = [
    discoveryengine.RankingRecord(
        id="1",
        title="",
        content="Python is a popular programming language known for its simplicity and readability."
    ),
    discoveryengine.RankingRecord(
        id="2",
        title="",
        content="The Python snake is one of the largest species of snakes in the world."
    ),
    discoveryengine.RankingRecord(
        id="3",
        title="",
        content="In Greek mythology, Python was a serpent killed by the god Apollo."
    ),
    discoveryengine.RankingRecord(
        id="4",
        title="",
        content="Python's extensive libraries and frameworks make it a versatile language for web development."
    ),
]
request = discoveryengine.RankRequest(
    ranking_config=ranking_config,
    model="semantic-ranker-512@latest",
    top_n=4, 
    query=query,
    records=records,
)

# Call the ranking API
response = client.rank(request=request)

# Print the ranking results
for record in response.records:
    print(f"ID: {record.id}, Score: {record.score:.2f}, Content: {record.content}")
