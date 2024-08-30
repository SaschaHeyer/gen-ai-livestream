import vertexai
from vertexai.generative_models import (
    Content,
    FunctionDeclaration,
    GenerationConfig,
    GenerativeModel,
    Tool,
    Part,
    AutomaticFunctionCallingResponder,
)

# Initialize Vertex AI
project_id = "sascha-playground-doit"
vertexai.init(project=project_id, location="us-central1")

# Define the functions to be used by the model
def get_order_status(order_id: str):
    # Simulated response
    return {
        "order_id": order_id,
        "expected_delivery": "Tomorrow"
    }

def initiate_return(order_id: str, reason: str = "No reason provided"):
    # Simulated response
    return {
        "order_id": order_id,
        "return_status": "Return initiated successfully.",
        "return_label": "You will receive a return label shortly."
    }

# Infer function schema from the defined functions
get_order_status_func = FunctionDeclaration.from_func(get_order_status)
initiate_return_func = FunctionDeclaration.from_func(initiate_return)

# Tool is a collection of related functions
order_tool = Tool(
    function_declarations=[get_order_status_func, initiate_return_func],
)

# Initialize the model with the tool and set up automatic function calling
model = GenerativeModel(
    model_name="gemini-1.5-flash-001",
    system_instruction="You are a store support API assistant to help with online orders.",
    tools=[order_tool],
)

# Activate automatic function calling
afc_responder = AutomaticFunctionCallingResponder(
    max_automatic_function_calls=5,
)

# Start a chat with the responder
chat = model.start_chat(responder=afc_responder)
#chat = model.start_chat()

# Define the user's prompt
user_prompt_content = Content(
    role="user",
    parts=[
        Part.from_text("What's the status of my order ID #12345?"),
    ],
)

# Send a message to the model and get the response
response = chat.send_message("What's the status of my order ID #12345?")

# Output the final response
print(response.text)
