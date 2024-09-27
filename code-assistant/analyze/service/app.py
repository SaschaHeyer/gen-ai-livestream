import os
import shutil
import sys
from pathlib import Path
import tempfile

import git
import magika
import requests
import streamlit as st
import vertexai
from vertexai.generative_models import (
    FunctionDeclaration,
    GenerationConfig,
    GenerativeModel,
    Tool,
)

# Set up the Streamlit app with widescreen layout
st.set_page_config(layout="wide")
st.title("Codebase Analyzer with Vertex AI Gemini 1.5")

# Input for Google Cloud Project ID
PROJECT_ID = "sascha-playground-doit"
LOCATION = "us-central1"

# Input for GitHub URL
repo_url = st.text_input(
    "Enter the GitHub repository URL",
    value="https://github.com/SaschaHeyer/gen-ai-livestream",
)

# Model selection dropdown
MODEL_ID = st.selectbox(
    "Select the Vertex AI model",
    options=["gemini-1.5-flash-002", "gemini-1.5-pro-002"],
    index=0,  # Default to gemini-1.5-pro-002
)

# Questions to ask
questions = [
    "Give me a summary of this codebase, and tell me the top 3 things that I can learn from it.",
    "Provide a getting started guide to onboard new developers to the codebase.",
    "Evaluate the codebase for maintainability and suggest ways to reduce technical debt.",
    "Provide a high-level architecture based on the current structure of the codebase.",
    "Identify and suggest improvements for code duplication across the codebase.",
    "How can I improve the test coverage for this codebase? Suggest areas with missing or insufficient tests.",
    "How can I refactor the most complex function or class to make it simpler and more maintainable?",
    "Find the top 3 most severe issues in the codebase.",
    "Find the most severe bug in the codebase that you can provide a code fix for.",
    "Create a troubleshooting guide to help resolve common issues.",
    "How can I make this application more reliable? Consider best practices from https://www.r9y.dev/",
    "How can you secure the application?",
    "Create a quiz about the concepts used in my codebase to help me solidify my understanding.",
]

# Allow user to select questions
selected_questions = st.multiselect(
    "Select questions to run", questions, default=questions
)

# Button to start analysis
if st.button("Analyze"):
    if not PROJECT_ID or not LOCATION:
        st.error("Please enter your Google Cloud Project ID and Location.")
    else:
        # Initialize Vertex AI SDK
        vertexai.init(project=PROJECT_ID, location=LOCATION)

        # The location to clone the repo (use a temporary directory)
        repo_dir = tempfile.mkdtemp()

        # Clone the repo
        with st.spinner("Cloning repository..."):
            try:
                git.Repo.clone_from(repo_url, repo_dir)
                st.success("Repository cloned successfully.")
            except Exception as e:
                st.error(f"Error cloning repository: {e}")
                sys.exit(1)

        # Extract code
        with st.spinner("Extracting code..."):
            m = magika.Magika()
            code_index = []
            code_text = ""
            for root, _, files in os.walk(repo_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, repo_dir)
                    code_index.append(relative_path)

                    file_type = m.identify_path(Path(file_path))
                    if file_type.output.group in ("text", "code"):
                        try:
                            with open(file_path, encoding="utf-8") as f:
                                code_text += f"----- File: {relative_path} -----\n"
                                code_text += f.read()
                                code_text += "\n-------------------------\n"
                        except Exception:
                            pass
            st.success("Code extracted successfully.")

        # Load the selected model
        model = GenerativeModel(
            MODEL_ID,
            system_instruction=[
                "You are a coding expert.",
                "Your mission is to answer all code related questions with given context and instructions.",
            ],
        )

        # Function to generate prompt
        def get_code_prompt(question):
            """Generates a prompt to a code related question."""
            prompt = f"""
Questions: {question}

Context:
- The entire codebase is provided below.
- Here is an index of all of the files in the codebase:
{code_index}

- Then each of the files is concatenated together. You will find all of the code you need:

{code_text}

Answer:
"""
            return prompt

        # For each selected question, generate and display the answer
        for question in selected_questions:
            st.subheader(question)
            prompt = get_code_prompt(question)
            contents = [prompt]
            with st.spinner("Generating response..."):
                try:
                    response = model.generate_content(contents)
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Error generating response: {e}")

        # Clean up the temporary directory
        shutil.rmtree(repo_dir)
