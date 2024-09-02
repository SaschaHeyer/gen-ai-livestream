import json
import os
from flask import Flask, request, jsonify
import vertexai
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig

app = Flask(__name__)

prompt = """
You are a document entity extraction specialist. 
Given a document, your task is to extract the text value of entities.
- Generate null for missing entities.
"""

def generate(pdf_bytes):
    vertexai.init(project="sascha-playground-doit", location="us-central1")

    RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "invoice_number": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "quantity": {"type": "string"},
                    "total": {"type": "string"}
                },
                "required": ["description", "quantity", "price", "total"]
            }
        }
    }
}
    # Initialize the model with the controlled JSON output configuration
    model = GenerativeModel("gemini-1.5-pro-001")

    generation_config = GenerationConfig(
        max_output_tokens=8192,
        temperature=0,
        top_p=0.95,
        response_mime_type="application/json",
        response_schema=RESPONSE_SCHEMA
    )
    
    # Create a Part from data (bytes)
    document_part = Part.from_data(data=pdf_bytes, mime_type="application/pdf")

    # Log the inputs to help with debugging
    print(f"Using prompt: {prompt}")
    print(f"Document Part: {document_part}")

    responses = model.generate_content(
        [document_part, prompt],
        generation_config=generation_config,
    )

    print(f"Raw response: {responses}")

    if responses and responses.candidates:
        json_response = responses.candidates[0].content.parts[0].text
        print(f"Generated JSON response: {json_response}")
    else:
        json_response = "{}"

    return json_response

@app.route('/process_pdf', methods=['POST'])
def process_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and file.filename.endswith('.pdf'):
        pdf_bytes = file.read()  # Read the file content into memory
        json_output = generate(pdf_bytes)
        return jsonify(json.loads(json_output)), 200
    
    return jsonify({"error": "Invalid file type"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
