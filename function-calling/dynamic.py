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
        # Part.from_text("I want to return my order with ID #12345?")
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

# Define dummy functions for each operation
def get_order_status(args):
    order_id = args.get("order_id")
    # Simulated response
    return {
        "order_id": order_id,
        "expected_delivery": "Tomorrow"
    }

def initiate_return(args):
    order_id = args.get("order_id")
    reason = args.get("reason", "No reason provided")
    # Simulated response
    return {
        "order_id": order_id,
        "return_status": "Return initiated successfully.",
        "return_label": "You will receive a return label shortly."
    }

# Map function names to their handlers
function_handlers = {
    "get_order_status": get_order_status,
    "initiate_return": initiate_return,
}

# Iterate over all the function calls in the model's response
for function_call in response.candidates[0].function_calls:
    print(function_call)
    function_name = function_call.name
    args = {key: value for key, value in function_call.args.items()}
    
    if function_name in function_handlers:
        # Call the appropriate function with the extracted arguments
        api_response = function_handlers[function_name](args)

        # Return the dummy API response to Gemini so it can generate a model response or request another function call
        response = model.generate_content(
            [
                user_prompt_content,  # User prompt
                response.candidates[0].content,  # Function call response
                Content(
                    parts=[
                        Part.from_function_response(
                            name=function_call.name,
                            response={"content": api_response},  # Return the function response to Gemini
                        ),
                    ],
                ),
            ],
            tools=[support_tool],
        )

        # Get the model response and print it
        print(response.text)
