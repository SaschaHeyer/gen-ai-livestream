import streamlit as st
import base64
from google import genai
from google.genai import types
from google.cloud import vision
import tempfile
import os
import json
import time

def gemini_content_moderation(image_bytes):
    """Content moderation using Google Gemini"""
    try:
        start_time = time.time()
        
        client = genai.Client(
            vertexai=True,
            project="sascha-playground-doit",
            location="us-central1",
        )

        msg1_image1 = types.Part.from_bytes(
            data=image_bytes,
            mime_type="image/png",
        )

        si_text1 = """you are a content moderation expert. Is this picture is safe or not in terms of: toxic, terrorism, violence, nudity, weapons."""

        model = "gemini-2.0-flash-001"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text="""categorize"""),
                    msg1_image1
                ]
            ),
        ]

        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            top_p=1,
            max_output_tokens=8192,
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_HATE_SPEECH",
                    threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_DANGEROUS_CONTENT",
                    threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_HARASSMENT",
                    threshold="OFF"
                )
            ],
            response_mime_type="application/json",
            response_schema={"type": "OBJECT", "properties": {"category": {"type": "STRING", "enum": ["abusive", "ok"]}}},
            system_instruction=[types.Part.from_text(text=si_text1)],
        )

        # Use non-streaming response
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )
        
        end_time = time.time()
        response_time_ms = round((end_time - start_time) * 1000)
        
        # Calculate cost based on token usage
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count
        output_tokens = usage.candidates_token_count
        
        # Pricing: Input $0.15/1M tokens, Output $0.60/1M tokens
        input_cost = (input_tokens / 1_000_000) * 0.15
        output_cost = (output_tokens / 1_000_000) * 0.60
        total_cost = input_cost + output_cost
        
        result = json.loads(response.text)
        result.update({
            "response_time_ms": response_time_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": usage.total_token_count,
            "cost_usd": round(total_cost, 6)
        })
        
        return result
    except Exception as e:
        return {"error": str(e)}

def vision_api_content_moderation(image_bytes):
    """Content moderation using Cloud Vision API"""
    try:
        start_time = time.time()
        
        client = vision.ImageAnnotatorClient()

        image = vision.Image(content=image_bytes)
        response = client.safe_search_detection(image=image)
        safe = response.safe_search_annotation

        end_time = time.time()
        response_time_ms = round((end_time - start_time) * 1000)

        likelihood_name = (
            "UNKNOWN",
            "VERY_UNLIKELY",
            "UNLIKELY",
            "POSSIBLE",
            "LIKELY",
            "VERY_LIKELY",
        )

        if response.error.message:
            return {"error": response.error.message}

        # Vision API pricing: $1.50 per 1000 units for Safe Search Detection
        cost_usd = 0.0015  # Cost per request
        
        return {
            "adult": likelihood_name[safe.adult],
            "medical": likelihood_name[safe.medical],
            "spoofed": likelihood_name[safe.spoof],
            "violence": likelihood_name[safe.violence],
            "racy": likelihood_name[safe.racy],
            "response_time_ms": response_time_ms,
            "cost_usd": cost_usd
        }
    except Exception as e:
        return {"error": str(e)}

def main():
    st.set_page_config(page_title="Content Moderation Comparison", layout="wide")

    st.title("Content Moderation System Comparison")
    st.write("Compare Google Gemini vs Cloud Vision API for content moderation")

    # Create main layout: left sidebar for input, right area for results
    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.subheader("Input")
        uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

        if uploaded_file is not None:
            image_bytes = uploaded_file.read()
            st.image(image_bytes, caption="Uploaded Image", width=300)

            run_analysis = st.button("Run Content Moderation", use_container_width=True)
        else:
            run_analysis = False

    with right_col:
        st.subheader("Analysis Results")

        if uploaded_file is not None and run_analysis:
            # Create two columns for the results
            gemini_col, vision_col = st.columns(2)

            with gemini_col:
                st.markdown("### 🔮 Google Gemini")
                with st.spinner("Analyzing with Gemini..."):
                    gemini_result = gemini_content_moderation(image_bytes)

                if "error" in gemini_result:
                    st.error(f"Error: {gemini_result['error']}")
                else:
                    # Display performance metrics
                    if "response_time_ms" in gemini_result:
                        st.metric("Response Time", f"{gemini_result['response_time_ms']} ms")
                        st.metric("Cost (per image)", f"${gemini_result['cost_usd']:.6f}")
                        
                        # Calculate and display cost for 100k images
                        cost_100k = gemini_result['cost_usd'] * 100000
                        st.metric("Cost (100k images)", f"${cost_100k:.2f}")
                        
                        # Display token usage
                        st.caption(f"Tokens: {gemini_result['input_tokens']} input + {gemini_result['output_tokens']} output = {gemini_result['total_tokens']} total")

                    # Remove performance data from JSON display
                    display_result = {k: v for k, v in gemini_result.items() 
                                    if k not in ["response_time_ms", "cost_usd", "input_tokens", "output_tokens", "total_tokens"]}
                    st.json(display_result)

                    if gemini_result.get("category") == "ok":
                        st.success("✅ Content is SAFE")
                    else:
                        st.error("❌ Content is UNSAFE")

            with vision_col:
                st.markdown("### 👁️ Cloud Vision API")
                with st.spinner("Analyzing with Vision API..."):
                    vision_result = vision_api_content_moderation(image_bytes)

                if "error" in vision_result:
                    st.error(f"Error: {vision_result['error']}")
                else:
                    # Display performance metrics
                    if "response_time_ms" in vision_result:
                        st.metric("Response Time", f"{vision_result['response_time_ms']} ms")
                        st.metric("Cost (per image)", f"${vision_result['cost_usd']:.4f}")
                        
                        # Calculate and display cost for 100k images
                        cost_100k = vision_result['cost_usd'] * 100000
                        st.metric("Cost (100k images)", f"${cost_100k:.2f}")

                    # Remove performance data from JSON display
                    display_result = {k: v for k, v in vision_result.items() 
                                    if k not in ["response_time_ms", "cost_usd"]}
                    st.json(display_result)

                    # Determine overall safety based on Vision API results
                    unsafe_categories = []
                    for category, likelihood in display_result.items():
                        if likelihood in ["LIKELY", "VERY_LIKELY"]:
                            unsafe_categories.append(category)

                    if unsafe_categories:
                        st.error(f"❌ Content is UNSAFE - {', '.join(unsafe_categories)}")
                    else:
                        st.success("✅ Content is SAFE")
        else:
            st.info("👆 Upload an image and click 'Run Content Moderation' to see results")

if __name__ == "__main__":
    main()
