def list_and_delete_all_corpora(project_id: str):
    from vertexai.preview import rag
    import vertexai

    # Initialize Vertex AI API once per session
    vertexai.init(project=project_id, location="us-central1")

    # List all corpora
    corpora = rag.list_corpora()

    # If there are corpora, proceed to delete them
    if corpora:
        print("Listing and deleting all corpora:")
        for corpus in corpora:
            print(f"Deleting corpus: {corpus.name}")
            rag.delete_corpus(name=corpus.name)
            print(f"Deleted corpus: {corpus.name}")
    else:
        print("No corpora found.")

    return corpora

# Example usage
project_id = "sascha-playground-doit"
list_and_delete_all_corpora(project_id)
