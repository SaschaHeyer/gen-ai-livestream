from google.cloud import discoveryengine_v1alpha as discoveryengine
import logging

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

# Define the base query
base_query = "Which language can I use for web development?"

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

# Start with a base query length and increase until an error occurs
query_length = len(base_query)
step = 10000  # Number of characters to increase with each iteration
max_attempts = 100  # Maximum number of attempts to avoid an infinite loop

for attempt in range(max_attempts):
    try:
        # Increase the query length by appending 'x'
        query = base_query + 'x' * (query_length - len(base_query))
        #print(query)

        # Create the request with the current query
        request = discoveryengine.RankRequest(
            ranking_config=ranking_config,
            model="semantic-ranker-512@latest",
            top_n=4,
            query=query,
            records=records,
        )

        # Call the ranking API
        response = client.rank(request=request)

        # Print the length of the query and the response
        print(f"Query length: {query_length} - Success")

        # Increase the query length for the next attempt
        query_length += step

    except Exception as e:
        # Print the error and stop the loop
        print(f"Query length: {query_length} - Failed with error: {e}")
        break
