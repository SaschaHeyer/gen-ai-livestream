import streamlit as st
import base64
from google import genai
from google.genai import types
from google.cloud import vision
import tempfile
import os
import json
import time
import boto3

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

        si_text1 = """you are a content moderation expert. Is this picture is safe or not in terms of: toxic, terrorism, violence, nudity, weapons, guns, drugs, abusive."""

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
            temperature=0,
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
            response_schema={"type": "OBJECT", "properties": {"category": {"type": "STRING", "enum": ["unsafe", "ok"]}}},
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

        # Pricing: Input $0.10/1M tokens, Output $0.40/1M tokens
        input_cost = (input_tokens / 1_000_000) * 0.10
        output_cost = (output_tokens / 1_000_000) * 0.40
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

def rekognition_content_moderation(image_bytes):
    """Content moderation using AWS Rekognition"""
    try:
        start_time = time.time()

        # Create Rekognition client
        rekognition = boto3.client('rekognition')

        # Detect moderation labels
        response = rekognition.detect_moderation_labels(
            Image={'Bytes': image_bytes},
            MinConfidence=0  # Get all labels regardless of confidence
        )

        end_time = time.time()
        response_time_ms = round((end_time - start_time) * 1000)

        # AWS Rekognition pricing: $0.001 per image for content moderation
        cost_usd = 0.001

        # Process moderation labels
        moderation_labels = response.get('ModerationLabels', [])

        # Categorize the results
        unsafe_categories = []
        label_details = {}

        for label in moderation_labels:
            name = label['Name']
            confidence = label['Confidence']
            label_details[name] = confidence

            # Consider anything above 50% confidence as unsafe
            if confidence > 50:
                unsafe_categories.append(name)

        # Determine overall category
        category = "abusive" if unsafe_categories else "ok"

        result = {
            "category": category,
            "response_time_ms": response_time_ms,
            "cost_usd": cost_usd
        }

        return result

    except Exception as e:
        return {"error": str(e)}

def main():
    st.set_page_config(page_title="Content Moderation Comparison", layout="wide")

    st.title("Content Moderation System Comparison")
    st.write("Compare Google Gemini vs Cloud Vision API vs AWS Rekognition for content moderation")

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
            # Get results from all services first
            with st.spinner("Analyzing with all services..."):
                gemini_result = gemini_content_moderation(image_bytes)
                vision_result = vision_api_content_moderation(image_bytes)
                rekognition_result = rekognition_content_moderation(image_bytes)

            # Calculate price percentages for comparison
            costs = {}
            if "error" not in gemini_result and "cost_usd" in gemini_result:
                costs["gemini"] = gemini_result["cost_usd"]
            if "error" not in vision_result and "cost_usd" in vision_result:
                costs["vision"] = vision_result["cost_usd"]
            if "error" not in rekognition_result and "cost_usd" in rekognition_result:
                costs["rekognition"] = rekognition_result["cost_usd"]

            min_cost = min(costs.values()) if costs else 0

            # Create three columns for the results
            gemini_col, vision_col, rekognition_col = st.columns(3)

            with gemini_col:
                st.markdown("### 🔮 Google Gemini")

                if "error" in gemini_result:
                    st.error(f"Error: {gemini_result['error']}")
                else:
                    # Display performance metrics
                    if "response_time_ms" in gemini_result:
                        st.metric("Response Time", f"{gemini_result['response_time_ms']} ms")

                        # Calculate percentage more expensive
                        cost = gemini_result['cost_usd']
                        if min_cost > 0:
                            percentage_more = ((cost - min_cost) / min_cost * 100) if cost > min_cost else 0
                            cost_label = f"${cost:.6f}" + (f" (+{percentage_more:.0f}%)" if percentage_more > 0 else " (Cheapest)")
                        else:
                            cost_label = f"${cost:.6f}"
                        st.metric("Cost (per image)", cost_label)

                        # Calculate and display cost for 100k images
                        cost_100k = cost * 100000
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

                if "error" in vision_result:
                    st.error(f"Error: {vision_result['error']}")
                else:
                    # Display performance metrics
                    if "response_time_ms" in vision_result:
                        st.metric("Response Time", f"{vision_result['response_time_ms']} ms")

                        # Calculate percentage more expensive
                        cost = vision_result['cost_usd']
                        if min_cost > 0:
                            percentage_more = ((cost - min_cost) / min_cost * 100) if cost > min_cost else 0
                            cost_label = f"${cost:.4f}" + (f" (+{percentage_more:.0f}%)" if percentage_more > 0 else " (Cheapest)")
                        else:
                            cost_label = f"${cost:.4f}"
                        st.metric("Cost (per image)", cost_label)

                        # Calculate and display cost for 100k images
                        cost_100k = cost * 100000
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

            with rekognition_col:
                st.markdown("### 🔍 AWS Rekognition")

                if "error" in rekognition_result:
                    st.error(f"Error: {rekognition_result['error']}")
                else:
                    # Display performance metrics
                    if "response_time_ms" in rekognition_result:
                        st.metric("Response Time", f"{rekognition_result['response_time_ms']} ms")

                        # Calculate percentage more expensive
                        cost = rekognition_result['cost_usd']
                        if min_cost > 0:
                            percentage_more = ((cost - min_cost) / min_cost * 100) if cost > min_cost else 0
                            cost_label = f"${cost:.4f}" + (f" (+{percentage_more:.0f}%)" if percentage_more > 0 else " (Cheapest)")
                        else:
                            cost_label = f"${cost:.4f}"
                        st.metric("Cost (per image)", cost_label)

                        # Calculate and display cost for 100k images
                        cost_100k = cost * 100000
                        st.metric("Cost (100k images)", f"${cost_100k:.2f}")

                    # Remove performance data from JSON display
                    display_result = {k: v for k, v in rekognition_result.items()
                                    if k not in ["response_time_ms", "cost_usd"]}
                    st.json(display_result)

                    if rekognition_result.get("category") == "ok":
                        st.success("✅ Content is SAFE")
                    else:
                        st.error("❌ Content is UNSAFE")
        else:
            st.info("👆 Upload an image and click 'Run Content Moderation' to see results")

if __name__ == "__main__":
    main()
