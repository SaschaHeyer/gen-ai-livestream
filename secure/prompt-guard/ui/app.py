import streamlit as st
import requests
import time
import matplotlib.pyplot as plt

# API endpoints
cpu_url = "https://prompt-guard-api-cpu-234439745674.us-central1.run.app/check_prompt"
gpu_url = "https://prompt-guard-api-gpu-234439745674.us-central1.run.app/check_prompt"

# Custom CSS to make the layout widescreen and match the styling of the provided slide
st.set_page_config(layout="wide")  # Set widescreen layout

st.markdown(
    """
    <style>
    body {
        background-color: #222222;
        color: white;
        font-family: 'sans-serif';
    }
    .header {
        background-color: #222222;
        color: white;
        padding: 20px;
        text-align: center;
        font-size: 36px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .container {
        width: 90%;
        margin: 0 auto;
    }
    .stTextArea textarea {
        background-color: #333333;
        color: white;
    }
    .stButton button {
        background-color: #555555;
        color: white;
        border-radius: 5px;
        padding: 10px;
    }
    .stMetric {
        background-color: #333333;
        color: white;
    }
    h2 {
        color: white;
    }
    .jailbreak-alert {
        color: red;
        font-weight: bold;
        font-size: 1.5rem;
    }
    .safe-alert {
        color: green;
        font-weight: bold;
        font-size: 1.5rem;
    }
    .inference-time {
        font-size: 1.2rem;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# Header
st.markdown('<div class="header">Prompt Guard - CPU vs GPU Demo</div>', unsafe_allow_html=True)

# Input for the prompt
prompt = st.text_area("Enter your prompt:", placeholder="Type a prompt here...")

# Function to call the API with error handling and timeout
def call_api(url, prompt):
    try:
        start_time = time.time()
        response = requests.post(url, json={"prompt": prompt})
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        if response.status_code == 200:
            return response.json(), response_time
        else:
            return {"error": "Failed to get a valid response"}, response_time
    except requests.exceptions.Timeout:
        return {"error": "Request timed out"}, None
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}, None

# Button to run the prompt against both APIs
if st.button("Check Prompt"):
    if prompt:
        with st.spinner('Processing...'):
            # Call the CPU API
            cpu_response, cpu_time = call_api(cpu_url, prompt)

            # Call the GPU API
            gpu_response, gpu_time = call_api(gpu_url, prompt)

        # Check for errors and display the results
        if "error" not in cpu_response and "error" not in gpu_response:
            # Classification Section (Jailbreak Score)
            st.subheader("Classification")
            jailbreak_score = float(cpu_response.get('jailbreak_score', 0))

            if jailbreak_score >= 0.5:
                st.markdown(f'<p class="jailbreak-alert">Jailbreak Score: {jailbreak_score:.4f}</p>', unsafe_allow_html=True)
            else:
                st.markdown(f'<p class="safe-alert">Jailbreak Score: {jailbreak_score:.4f}</p>', unsafe_allow_html=True)

            # Below classification: Two columns for Response Time and Latency
            col1, col2 = st.columns(2)

            # Left column: Response times
            with col1:
                st.subheader("Response Times")
                st.metric("CPU Response Time", f"{cpu_time:.2f} ms")
                st.metric("GPU Response Time", f"{gpu_time:.2f} ms")

                # Bar chart comparison of response times with transparent background
                st.subheader("Response Time Comparison")
                labels = ["CPU", "GPU"]
                times = [cpu_time, gpu_time]

                fig, ax = plt.subplots()
                ax.bar(labels, times, color=['#555555', '#0072C6'])
                ax.set_ylabel('Response Time (ms)')
                ax.set_title('CPU vs GPU Response Time', color='white')
                
                # Set figure background to white and remove black background
                fig.patch.set_facecolor('white')
                ax.set_facecolor('white')
                st.pyplot(fig)

            # Right column: Latency (Inference Time)
            with col2:
                st.subheader("Latency (Inference Time)")
                cpu_inference_time = cpu_response.get('inference_time', 0)
                gpu_inference_time = gpu_response.get('inference_time', 0)

                st.metric("CPU Inference Time", f"{cpu_inference_time:.2f} ms")
                st.metric("GPU Inference Time", f"{gpu_inference_time:.2f} ms")

                # Bar chart comparison of inference times
                st.subheader("Inference Time Comparison")
                inference_times = [cpu_inference_time, gpu_inference_time]

                fig2, ax2 = plt.subplots()
                ax2.bar(labels, inference_times, color=['#555555', '#0072C6'])
                ax2.set_ylabel('Inference Time (ms)')
                ax2.set_title('CPU vs GPU Inference Time', color='white')

                # Set figure background to white and remove black background
                fig2.patch.set_facecolor('white')
                ax2.set_facecolor('white')
                st.pyplot(fig2)
                
        else:
            st.error(f"Error with CPU Response: {cpu_response.get('error')}")
            st.error(f"Error with GPU Response: {gpu_response.get('error')}")
    else:
        st.warning("Please enter a prompt.")
