import os
import streamlit as st
import vertexai
from vertexai.preview import rag
from vertexai.preview.generative_models import GenerativeModel, Tool

# Initialize the Vertex AI
vertexai.init(project="sascha-playground-doit", location="us-central1")

# Create documents directory if it doesn't exist
documents_dir = './documents'
if not os.path.exists(documents_dir):
    os.makedirs(documents_dir)

# Streamlit UI
st.title("Document Management & Question Answering with RAG")

# Full RAG Corpus ID (including project and location)
rag_corpus_id = st.text_input("RAG Corpus ID", value="projects/sascha-playground-doit/locations/us-central1/ragCorpora/569705352862367744")

# Initialize session state for file upload tracking
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

# Display number of files in the corpus as soon as a valid corpus ID is provided
if rag_corpus_id:
    try:
        # List files in the corpus and count them
        files = rag.list_files(corpus_name=rag_corpus_id)
        file_list = list(files)  # Convert to a list to make it iterable
        file_count = len(file_list)

        # Display the number of files in the corpus
        st.write(f"Number of files in the corpus: {file_count}")

        # Optionally display the file details
        #for file in file_list:
        #    st.write(file)

    except Exception as e:
        st.error(f"Failed to retrieve files from the corpus: {e}")

    # Initialize RAG retrieval tool
    rag_retrieval_tool = Tool.from_retrieval(
        retrieval=rag.Retrieval(
            source=rag.VertexRagStore(
                rag_resources=[rag.RagResource(rag_corpus=rag_corpus_id)],
                similarity_top_k=3,  
                vector_distance_threshold=0.5,  
            ),
        )
    )

    # Initialize RAG generative model
    rag_model = GenerativeModel(
        system_instruction="answer questions based on given context. alwayse include the source as url",
        model_name="gemini-1.5-flash-002", 
        tools=[rag_retrieval_tool]
    )

    # Section 1: File Upload
    st.header("Upload Documents to Corpus")
    uploaded_files = st.file_uploader("Drag and drop or select documents", accept_multiple_files=True, type=["txt", "pdf"])

    if uploaded_files:
        for uploaded_file in uploaded_files:
            if uploaded_file.name not in st.session_state.uploaded_files:
                # Save uploaded file to the documents directory
                file_path = os.path.join(documents_dir, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                print("upload")
                # Upload file to RAG
                try:
                    rag_file = rag.upload_file(corpus_name=rag_corpus_id, path=file_path)
                    st.session_state.uploaded_files.append(uploaded_file.name)  # Track uploaded file
                    st.success(f"Uploaded {uploaded_file.name} to the RAG corpus.")

                    # Delete the file after successful upload
                    os.remove(file_path)
                    st.info(f"Deleted {uploaded_file.name} from local storage.")
                except Exception as e:
                    st.error(f"Failed to upload {uploaded_file.name}: {e}")

    # Display a message if files have been uploaded
    if st.session_state.uploaded_files:
        st.write("Files already uploaded to the corpus:", ", ".join(st.session_state.uploaded_files))

    # Section 2: Question Answering
    st.header("Ask a Question")
    question = st.text_input("Enter your question here")

    if st.button("Get Answer"):
        if question:
            response = rag_model.generate_content(question)
            st.write("Answer:", response.text)
        else:
            st.warning("Please enter a question.")
else:
    st.warning("Please provide a valid RAG Corpus ID.")
