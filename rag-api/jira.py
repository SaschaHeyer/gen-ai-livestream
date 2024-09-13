 # Jira Example
jira_query = rag.JiraQuery(
        email="xxx@yyy.com",
        jira_projects=["project1", "project2"],
        custom_queries=["query1", "query2"],
        api_key="api_key",
        server_uri="server.atlassian.net"
    )

source = rag.JiraSource(
        queries=[jira_query],
    )

response = rag.import_files(
        corpus_name="projects/my-project/locations/REGION/ragCorpora/my-corpus-1",
        source=source,
        chunk_size=512,
        chunk_overlap=100,
    )