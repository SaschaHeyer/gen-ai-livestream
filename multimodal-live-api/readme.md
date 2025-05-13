# Exploring Google's Multimodal Live API: Code & Articles

Welcome to the official code repository for the article series on **Exploring Google's Multimodal Live API capabilities**! This repository hosts the companion code for a series of technical articles and blog posts designed to help developers understand and implement cutting-edge solutions using this powerful API on Google Cloud.

Whether you're looking to dive into multimodal interactions or real-time streaming, you'll find practical examples and resources here.

Watch the demo video ⬇️⬇️⬇️

[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/e627baGHbZ4/0.jpg)](https://www.youtube.com/watch?v=e627baGHbZ4)

## 🚀 The Article Series

This series aims to provide deep dives and practical guides into various aspects of Google's Multimodal Live API. Follow along to learn how to leverage these powerful tools in your own projects.

**Published Articles:**

1.  **[A Developer's Guide to Google's Multimodal Live API](https://medium.com/google-cloud/a-developers-guide-to-googles-multimodal-live-api-8c80b596e7b3)**
    * An introductory guide to understanding and using the Multimodal Live API for combined text, audio, and video processing.
    * **Companion Code:** [`multimodal-live-api/introduction.py`](./multimodal-live-api/introduction.py) - Demonstrates basic text-to-text and text-to-audio functionalities.

2.  **[Real-time Audio-to-Audio Streaming with Google's Multimodal Live API](https://medium.com/google-cloud/real-time-audio-to-audio-streaming-with-googles-multimodal-live-api-73b54277b022)**
    * Learn how to build applications that can stream audio input and receive audio output in real-time.
    * **Companion Code:** [`multimodal-live-api/audio-to-audio.py`](./multimodal-live-api/audio-to-audio.py) - Implements a real-time audio-to-audio streaming solution.

3.  **[Google Multimodal Live API Audio Transcription](https://medium.com/google-cloud/google-multimodal-live-api-audio-transcription-368d4d4e7a7c)**
    * Add real-time input and output audio transcription to your AI applications.
    * **Companion Code:** [`multimodal-live-api/audio-to-audio.py`](./multimodal-live-api/audio-to-audio.py) - Demonstrates how to enable and use real-time transcription features.

4.  **[Multimodal Live API Tooling](https://medium.com/google-cloud/multimodal-live-api-tooling-c7f018ff0291)**
    * Extend your voice assistant with function calling capabilities to interact with external services.
    * **Companion Code:** [`multimodal-live-api/audio-to-audio.py`](./multimodal-live-api/audio-to-audio.py) - Shows how to implement and use tools/function calling with the Live API.

Stay tuned as more articles and corresponding code examples are added to this series!

## 📂 Repository Structure

The code examples are organized into directories that typically correspond to the topics covered in the articles:

* **`/multimodal-live-api/`**: Contains Python scripts demonstrating the capabilities of the Google Multimodal Live API.
    * `introduction.py`: Basic setup and usage for text and audio output. This file corresponds to the first article, "[A Developer's Guide to Google's Multimodal Live API](https://medium.com/google-cloud/a-developers-guide-to-googles-multimodal-live-api-8c80b596e7b3)".
    * `audio-to-audio.py`: Advanced example for real-time bidirectional audio streaming. This file corresponds to the second article, "[Real-time Audio-to-Audio Streaming with Google's Multimodal Live API](https://medium.com/google-cloud/real-time-audio-to-audio-streaming-with-googles-multimodal-live-api-73b54277b022)", third article, "[Google Multimodal Live API Audio Transcription](https://medium.com/google-cloud/google-multimodal-live-api-audio-transcription-368d4d4e7a7c)", and fourth article, "[Multimodal Live API Tooling](https://medium.com/google-cloud/multimodal-live-api-tooling-c7f018ff0291)".

## ✨ What's Next?

This repository and the accompanying article series are actively being developed. Expect more content covering other exciting areas of Google's Multimodal Live API and related Generative AI on Google Cloud, including:

* Advanced use cases
* Deeper dives into specific API features
* Integrations with Googles ADK

Your feedback and suggestions are welcome as the series grows.

## 🔧 Getting Started

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/SaschaHeyer/gen-ai-livestream.git](https://github.com/SaschaHeyer/gen-ai-livestream.git)
    cd gen-ai-livestream
    ```
2.  **Navigate to the specific example directory** you're interested in (e.g., `cd multimodal-live-api`).
3.  **Follow the instructions** within the specific code files or any accompanying `README.md` files in those directories for setting up dependencies and running the examples. Most Python examples will require you to have the Google Cloud SDK configured and the necessary client libraries installed.

    Typically, you might need to install dependencies like:
    ```bash
    pip install google-cloud-aiplatform google-generativeai pyaudio soundfile numpy
    ```
    Ensure your Google Cloud project is set up with the necessary APIs enabled (e.g., Vertex AI API).

## 🤝 Connect & Contribute

I'm thrilled to share these insights and examples with the developer community!

* **Follow me on Medium:** [Sascha Heyer](https://medium.com/@saschaheyer)
* **Connect on LinkedIn:** [Sascha Heyer on LinkedIn](https://www.linkedin.com/in/saschaheyer/)
* **Subscribe on YouTube:** [Sascha Heyer's YouTube Channel](https://www.youtube.com/@SaschaHeyer)

While this repository primarily serves as a companion to the articles, feel free to raise issues for any bugs you find in the code or suggest improvements.

Happy coding, and I hope you find this series and the code examples valuable on your Generative AI journey!
