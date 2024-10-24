import vertexai
import json
from vertexai import generative_models
from vertexai.generative_models import GenerationConfig, GenerativeModel


# Define your response schema structure (_RESPONSE_SCHEMA_STRUCT)
_RESPONSE_SCHEMA_STRUCT = {
    "type": "object",
    "properties": {
        "recipe_title": {
            "type": "string",
            "description": "The recipe title."
        },
        "recipe_description": {
            "type": "string",
            "description": "The recipe description."
        },
        "ingredients": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the ingredient."
                    },
                    "quantity": {
                        "type": "string",
                        "description": "The quantity of the ingredient."
                    },
                    "unit": {
                        "type": "string",
                        "description": "The unit of measurement for the ingredient."
                    }
                },
                "required": ["name", "quantity"]  # Adjust required fields as needed
            }
        }
    },
    "required": ["recipe_title", "recipe_description"]
}

def generate():
    vertexai.init(project="sascha-playground-doit", location="us-central1")
    model = GenerativeModel("gemini-1.5-flash-001")

    generation_config = GenerationConfig(
        temperature=1.0,
        max_output_tokens=8192,
        response_mime_type="application/json",
        response_schema=_RESPONSE_SCHEMA_STRUCT
    )

    responses = model.generate_content(
        ["generate a recipe"],
        generation_config=generation_config,
        stream=False,
    )

    generation = responses.candidates[0].content.parts[0].text
    print(generation)


generate()