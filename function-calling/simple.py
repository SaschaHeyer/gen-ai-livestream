

from vertexai.generative_models import (
    FunctionDeclaration,
    GenerationConfig,
    GenerativeModel,
    Tool
)

#option 1
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

# Define the functions to be used by the model
def get_order_status(order_id: str):
    # Simulated response
    return {
        "order_id": order_id,
        "expected_delivery": "Tomorrow"
    }
 
# option 2   
get_order_status_func = FunctionDeclaration.from_func(get_order_status)


order_tool = Tool(
    function_declarations=[
        get_order_status_func,
    ],
)
    
model = GenerativeModel(
    "gemini-1.5-pro-001",
    generation_config=GenerationConfig(temperature=0),
    tools=[order_tool],
)
chat = model.start_chat()

prompt = "What is the capital of Berlin and can you check where my order with ID 12345 is?"
#prompt = "Can you check where my order with ID 12345 is?"

response = chat.send_message(prompt)
print(response.candidates[0].content)

function_calls = response.candidates[0].function_calls
print(function_calls)