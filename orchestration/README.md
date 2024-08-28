# Generative AI Orchestration
https://youtube.com/live/gAxQst87vA4

## Usage

### Deploy the workflow
```
gcloud workflows deploy recipe --source=recipe.yaml
```

### Run the workflow
```
gcloud workflows run recipe --data='{"recipePrompt":"generate a vegan BBQ recipe"}'
```