from flask import Flask, jsonify
import torch

app = Flask(__name__)

@app.route('/')
def gpu_info():
    if torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        gpu_name = torch.cuda.get_device_name(0)  # Assumes at least one GPU
        gpu_props = torch.cuda.get_device_properties(0)
        return jsonify({
            "GPU available": True,
            "GPU count": gpu_count,
            "GPU name": gpu_name,
            "Total memory": gpu_props.total_memory,
            "Major compute capability": gpu_props.major,
            "Minor compute capability": gpu_props.minor,
        })
    else:
        return jsonify({"GPU available": False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080) 