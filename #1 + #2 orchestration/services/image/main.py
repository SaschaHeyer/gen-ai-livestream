from flask import Flask, jsonify, request
import os
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from google.cloud import storage

project_id = "sascha-playground-doit"
#prompt = "generate a hotdog"
output_file = "temp_recipe.png"


vertexai.init(project=project_id, location="us-central1")

model = ImageGenerationModel.from_pretrained("imagegeneration@006")
storage_client = storage.Client()

app = Flask(__name__)

@app.route('/', methods=['POST'])
def generate_image():
    content = request.json
    uuid = content.get('uuid')  # Use the provided UUID or a default
    prompt = content.get('prompt')
    print(content)
    
   
    
    images = model.generate_images(
        prompt=prompt,
        # Optional parameters
        number_of_images=4,
        language="en",
        # You can't use a seed value and watermark at the same time.
        # add_watermark=False,
        # seed=100,
        aspect_ratio="16:9",
        safety_filter_level="block_some",
        #person_generation="allow_adult",
    )

    print(images)

    images[0].save(location=output_file, include_generation_parameters=False)

    print(f"Created output image using {len(images[0]._image_bytes)} bytes")

    destination_blob_name = f"recipes/{uuid}.png"
    bucket = storage_client.bucket("doit-llm")
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(output_file)

    print(f"File {output_file} uploaded to {destination_blob_name}.")

    
    
    return jsonify({
         "image_size": len(images[0]._image_bytes),
         "destination": destination_blob_name
    })

app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))