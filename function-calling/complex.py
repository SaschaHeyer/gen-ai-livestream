import requests
import vertexai
from vertexai.generative_models import (
    Content,
    FunctionDeclaration,
    GenerationConfig,
    GenerativeModel,
    Part,
    Tool,
)

# Initialize Vertex AI
project_id = "sascha-playground-doit"
vertexai.init(project=project_id, location="us-central1")

# Initialize Gemini model
model = GenerativeModel("gemini-1.5-flash-001",
                        system_instruction=["""You are a store support API assistant to help with online orders."""])

# Define the user's prompt in a Content object that we can reuse in model calls
user_prompt_content = Content(
    role="user",
    parts=[
        Part.from_text("What's the status of my order ID #12345?"),
        #Part.from_text("I want to return my order with ID #12345?")
    ],
)

# Define the function declarations
get_order_status_func = FunctionDeclaration(
    name="get_order_status",
    description="Retrieve the current status of an order by its order ID.",
    parameters={
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "The unique identifier of the order."
            }
        },
        "required": ["order_id"]
    },
)

initiate_return_func = FunctionDeclaration(
    name="initiate_return",
    description="Initiate a return process for a given order ID.",
    parameters={
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "The unique identifier of the order to be returned."
            }
        },
        "required": ["order_id"]
    },
)

# Define the tools that include the above functions
support_tool = Tool(
    function_declarations=[get_order_status_func, initiate_return_func],
)

# Send the prompt and instruct the model to generate content using the Tool that you just created
response = model.generate_content(
    user_prompt_content,
    generation_config=GenerationConfig(temperature=0),
    tools=[support_tool],
)

# Iterate over all the function calls in the model's response
for function_call in response.candidates[0].function_calls:
    print(function_call)

    # Prepare a dummy response based on the function name
    if function_call.name == "get_order_status":
        # Extract the arguments to simulate the data
        order_id = function_call.args["order_id"]

        # Dummy data for order status
        api_response = {
            "order_id": order_id,
            "expected_delivery": "Tomorrow"
        }

    elif function_call.name == "initiate_return":
        # Extract the arguments to simulate the data
        order_id = function_call.args["order_id"]
        reason = function_call.args.get("reason", "No reason provided")

        # Dummy data for initiating a return
        api_response = {
            "order_id": order_id,
            "return_status": "Return initiated successfully.",
            "return_label": "You will receive a return label shortly."
        }

    # Return the dummy API response to Gemini so it can generate a model response or request another function call
    response = model.generate_content(
        [
            user_prompt_content,  # User prompt
            response.candidates[0].content,  # Function call response
            Content(
                parts=[
                    Part.from_function_response(
                        name=function_call.name,
                        response={"content": api_response},  # Return the dummy API response to Gemini
                    ),
                ],
            ),
        ],
        tools=[support_tool],
    )

    # Get the model response and print it
    print(response.text)
