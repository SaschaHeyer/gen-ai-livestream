from google.cloud import trace_v1
from google.protobuf.timestamp_pb2 import Timestamp

client = trace_v1.TraceServiceClient()

project_id = "sascha-playground-doit"
trace_id = "29d5966ed47a129a5cfd34960b737528"

# Pricing per 1M tokens
PRICE_INPUT = 0.15  # $0.15 per 1M input tokens
PRICE_OUTPUT = 0.60  # $0.60 per 1M output tokens

# Get the trace
response = client.get_trace(project_id=project_id, trace_id=trace_id)

# Initialize counters
total_prompt_tokens = 0
total_completion_tokens = 0

# Process the spans from the trace
for span in response.spans:
    span_name = span.name
    
    # Process span attributes for token counts
    labels = span.labels
    if "llm.token_count.prompt" in labels or "llm.token_count.completion" in labels:
        prompt_tokens = int(labels.get('llm.token_count.prompt', 0))
        completion_tokens = int(labels.get('llm.token_count.completion', 0))
        
        total_prompt_tokens += prompt_tokens
        total_completion_tokens += completion_tokens
        
        print(f"Span: {span_name}")
        print(f"  Prompt tokens: {prompt_tokens}")
        print(f"  Completion tokens: {completion_tokens}")

# Calculate total tokens
total_tokens = total_prompt_tokens + total_completion_tokens

# Calculate costs
prompt_cost = (total_prompt_tokens / 1_000_000) * PRICE_INPUT
completion_cost = (total_completion_tokens / 1_000_000) * PRICE_OUTPUT
total_cost = prompt_cost + completion_cost

# Print totals and costs
print("\n" + "="*50)
print(f"Total prompt tokens: {total_prompt_tokens}")
print(f"Total completion tokens: {total_completion_tokens}")
print(f"Total tokens: {total_tokens}")
print("\nCosts:")
print(f"  Prompt cost: ${prompt_cost:.6f}")
print(f"  Completion cost: ${completion_cost:.6f}")
print(f"  Total cost: ${total_cost:.6f}")
