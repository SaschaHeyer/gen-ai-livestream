
import vertexai
from vertexai.preview import model_garden

vertexai.init(project="sascha-playground-doit", location="us-central1")

model_id = "google/gemma3@gemma-3-1b-it"
gemma_model = model_garden.OpenModel(model_id)

print(gemma_model.list_deploy_options())

gemma_endpoint = gemma_model.deploy(accept_eula=True)
print(gemma_endpoint)

prediction = gemma_endpoint.predict(
    instances=[{"prompt": "Tell me a joke about Berlin", "temperature": 0.7, "max_tokens": 50}]
)
print(prediction.predictions[0])
