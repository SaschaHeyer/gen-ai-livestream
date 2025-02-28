# Use the official PyTorch image as the base image
FROM pytorch/pytorch:2.0.0-cuda11.7-cudnn8-runtime

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Install Flask
RUN pip install Flask

# Expose the port that the app will run on
EXPOSE 8080

# Command to run the application
CMD ["python", "app.py"]
