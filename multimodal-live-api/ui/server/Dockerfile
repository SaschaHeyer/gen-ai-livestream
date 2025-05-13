FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server_adk.py .
COPY common.py .

# Expose the port the app runs on
EXPOSE 8765

# Run the application
CMD ["python", "server_adk.py"]