import requests
import json

# The URL of your deployed Cloud Run service
url = "https://document-understanding-234439745674.us-central1.run.app/process_pdf"

# The path to the PDF file you want to upload
pdf_file_path = "4.pdf"

# The custom response schema you provided earlier
custom_schema = {
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
                "required": ["description", "quantity", "total"]
            }
        }
    }
}

# Send the POST request with the PDF file and custom response schema
with open(pdf_file_path, 'rb') as pdf_file:
    files = {'file': pdf_file}
    data = {'response_schema': json.dumps(custom_schema)}  # Include the custom schema as form data
    response = requests.post(url, files=files, data=data)

# Check if the request was successful
if response.status_code == 200:
    print("Response JSON:")
    print(response.json())
else:
    print(f"Request failed with status code {response.status_code}")
    print(response.text)
