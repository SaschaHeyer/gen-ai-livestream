FROM python:3.8-slim

RUN pip install Flask==3.0.3 google-cloud-aiplatform==1.59.0 google-cloud-storage==2.17.0

WORKDIR /app
COPY . .

CMD python3 main.py