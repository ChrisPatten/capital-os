FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY . .
RUN pip install --no-cache-dir -e ".[mcp]"
RUN mkdir -p data
VOLUME ["/app/data"]
ENTRYPOINT ["/app/mcp/entrypoint.sh"]
