from vertexai.preview import model_garden

model_garden_models = model_garden.list_deployable_models(
    model_filter="gemma", list_hf_models=False
)

print(model_garden_models)
