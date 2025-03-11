# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container
COPY . /app

# Add a comment about environment variables
# NOTE: DO NOT include .env file in production
# Environment variables should be set in the Cloud Run configuration
# or using a secret manager

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Run webhook.py when the container launches
CMD ["python", "webhook.py"]
