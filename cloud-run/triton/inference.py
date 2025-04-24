import tritonclient.http as httpclient
import numpy as np
import tensorflow as tf
import time

triton_url = "triton-gpu-234439745674.us-central1.run.app"
model_name = "categorizer"

# Read raw JPEG image
with open("sample.jpg", "rb") as f:
    img_bytes = f.read()

client = httpclient.InferenceServerClient(url=triton_url, ssl=True)

# Prepare input
input_tensor = httpclient.InferInput("images", [1, 1], "BYTES")
input_tensor.set_data_from_numpy(np.array([[img_bytes]], dtype=object), binary_data=True)

# ⏱️ Start timer
start = time.time()

# Inference
result = client.infer(
    model_name=model_name,
    inputs=[input_tensor]
)

# ⏱️ End timer
end = time.time()
duration_ms = (end - start) * 1000
print(f"\n⚡ Inference time: {duration_ms:.2f} ms")

# Metadata
print("\n📦 Raw Triton response metadata:")
print(result.get_response())

# Output tensors
print("\n🧠 Model outputs:")
print("classes:", result.as_numpy("classes"))
print("scores:", result.as_numpy("scores"))
