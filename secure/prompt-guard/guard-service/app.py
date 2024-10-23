import os
import time
import torch
from flask import Flask, request, jsonify
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from torch.nn.functional import softmax

# Load the Prompt Guard model and tokenizer
prompt_injection_model_name = 'meta-llama/Prompt-Guard-86M'
tokenizer = AutoTokenizer.from_pretrained(prompt_injection_model_name)
model = AutoModelForSequenceClassification.from_pretrained(prompt_injection_model_name)

# Detect if GPU is available, otherwise use CPU
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model.to(device)

app = Flask(__name__)

# Function to get class probabilities for a batch of texts
def process_text_batch(texts, temperature=1.0, device='cpu'):
    inputs = tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length=512)
    inputs = inputs.to(device)
    with torch.no_grad():
        logits = model(**inputs).logits
    scaled_logits = logits / temperature
    probabilities = softmax(scaled_logits, dim=-1)
    
    return probabilities

# Function to compute scores for long texts using chunking
def get_scores_for_text(text, temperature=1.0, device='cpu', max_batch_size=16):
    # Split the text into chunks of 512 tokens
    chunks = [text[i:i + 512] for i in range(0, len(text), 512)]
    all_scores = {"jailbreak_score": 0, "indirect_injection_score": 0}
    
    # Process the chunks in batches
    for i in range(0, len(chunks), max_batch_size):
        batch_chunks = chunks[i:i + max_batch_size]
        probabilities = process_text_batch(batch_chunks, temperature, device)
        
        # Extract jailbreak and indirect injection scores for each chunk
        jailbreak_scores = probabilities[:, 2].tolist()
        indirect_injection_scores = (probabilities[:, 1] + probabilities[:, 2]).tolist()
        
        # Find the maximum score across chunks
        all_scores["jailbreak_score"] = max(all_scores["jailbreak_score"], max(jailbreak_scores))
        all_scores["indirect_injection_score"] = max(all_scores["indirect_injection_score"], max(indirect_injection_scores))
    
    return all_scores

# Function to format the score to show four decimal places
def format_score(score):
    return "{:.4f}".format(score)

@app.route("/check_prompt", methods=["POST"])
def check_prompt():
    data = request.get_json()
    prompt = data.get("prompt", "")
    
    start_time = time.time()
    
    # Get the scores for the input prompt, handling chunking and batching
    scores = get_scores_for_text(prompt, device=device)
    
    execution_time_ms = (time.time() - start_time) * 1000
    print(f"Execution time: {execution_time_ms:.3f} ms")
   
    # Format the scores to four decimal places
    formatted_jailbreak_score = format_score(scores["jailbreak_score"])
    formatted_indirect_injection_score = format_score(scores["indirect_injection_score"])
    
    # Return the results as a JSON response
    return jsonify({
        "inference_time": execution_time_ms,
        "jailbreak_score": formatted_jailbreak_score,
        "indirect_injection_score": formatted_indirect_injection_score
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
