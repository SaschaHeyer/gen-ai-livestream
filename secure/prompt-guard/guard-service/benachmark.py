import time
import requests

# Helper function to measure response time
def measure_response_time(url, prompt):
    start_time = time.time()
    response = requests.post(url, json={"prompt": prompt})
    total_time = time.time() - start_time
    return response.json(), total_time * 1000  # Convert seconds to ms

# Helper function to calculate average response time
def average_response_time(url, prompt, num_runs):
    total_time = 0
    for _ in range(num_runs):
        _, response_time = measure_response_time(url, prompt)
        total_time += response_time
    return total_time / num_runs

# Cloud Run service URLs (replace with actual URLs after deployment)
cpu_url = "https://prompt-guard-api-cpu-234439745674.us-central1.run.app/check_prompt"
gpu_url = "https://prompt-guard-api-gpu-234439745674.us-central1.run.app/check_prompt"
prompt = "whats the weather in berlin?"

# Measure cold start times
print("Measuring cold start for CPU-only service...")
_, cpu_cold_start_time = measure_response_time(cpu_url, prompt)
print(f"CPU-only service cold start time: {cpu_cold_start_time:.2f} ms")

print("Measuring cold start for GPU-enabled service...")
_, gpu_cold_start_time = measure_response_time(gpu_url, prompt)
print(f"GPU-enabled service cold start time: {gpu_cold_start_time:.2f} ms")

# Number of times to run the measurement for averaging
num_runs = 50

# Measure warmed-up response times (send a few requests to warm up the services)
print("Warming up services...")

# Warm-up CPU
for _ in range(5):
    measure_response_time(cpu_url, prompt)

# Warm-up GPU
for _ in range(5):
    measure_response_time(gpu_url, prompt)

# Measure response times again after warm-up and calculate average
print(f"Measuring average response time after warm-up over {num_runs} runs...")

# CPU average response time
cpu_avg_response_time = average_response_time(cpu_url, prompt, num_runs)
print(f"Average CPU-only service response time: {cpu_avg_response_time:.2f} ms")

# GPU average response time
gpu_avg_response_time = average_response_time(gpu_url, prompt, num_runs)
print(f"Average GPU-enabled service response time: {gpu_avg_response_time:.2f} ms")
