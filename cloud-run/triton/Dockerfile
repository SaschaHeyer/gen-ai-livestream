FROM nvcr.io/nvidia/tritonserver:23.12-py3

COPY models /models

ENTRYPOINT /opt/tritonserver/bin/tritonserver \
  --model-repository=/models \
  --http-port=8080
