import requests

# The URL of your deployed Cloud Run service
url = "https://document-understanding-xgdxnb6fdq-uc.a.run.app/process_pdf"

# The path to the PDF file you want to upload
pdf_file_path = "4.pdf"

# Send the POST request with the PDF file
with open(pdf_file_path, 'rb') as pdf_file:
    files = {'file': pdf_file}
    response = requests.post(url, files=files)

# Check if the request was successful
if response.status_code == 200:
    print("Response JSON:")
    print(response.json())
else:
    print(f"Request failed with status code {response.status_code}")
    print(response.text)
