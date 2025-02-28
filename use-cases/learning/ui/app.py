import streamlit as st
from google.cloud import firestore

# Initialize Firestore client
def get_firestore_client():
    return firestore.Client()

# Fetch all documents from a Firestore collection
def fetch_firestore_entries(collection_name):
    client = get_firestore_client()
    collection_ref = client.collection(collection_name)
    docs = collection_ref.stream()
    data = []
    for doc in docs:
        doc_data = doc.to_dict()
        doc_data['id'] = doc.id  # Add the document ID for reference
        data.append(doc_data)
    return data

# Streamlit app
def main():
    st.title("Firestore Entries Viewer")

    # Input for collection name
    collection_name = st.text_input("Enter Firestore Collection Name", "example_collection")

    # Fetch and display data
    if st.button("Fetch Entries"):
        try:
            st.info(f"Fetching entries from Firestore collection: {collection_name}")
            data = fetch_firestore_entries(collection_name)
            if data:
                st.success(f"Fetched {len(data)} entries.")
                # Display data as a table
                st.write(data)  # For structured JSON data
                # Use pandas for a tabular view
                import pandas as pd
                df = pd.DataFrame(data)
                st.dataframe(df)
            else:
                st.warning("No entries found in the specified collection.")
        except Exception as e:
            st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
