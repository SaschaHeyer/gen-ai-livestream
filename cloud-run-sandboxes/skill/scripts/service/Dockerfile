FROM python:3.12-slim

# curl is here so a sandboxed script has a real egress tool to try (and get blocked)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV PORT=8080
CMD ["gunicorn", "-b", ":8080", "main:app", "--timeout", "120", "--workers", "2"]
