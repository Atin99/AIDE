FROM python:3.12-slim

WORKDIR /app

# Install only the backend runtime dependencies needed by the Space.
COPY backend/requirements.api.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Hugging Face Spaces run on port 7860 by default
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7860
ENV AIDE_USE_LOCAL_LLM=0
ENV AIDE_ENABLE_REMOTE_LLM=1
ENV AIDE_USE_LOCAL_INTENT=0

# Expose the port
EXPOSE 7860

# Run the FastAPI application on port 7860
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "7860", "--timeout-keep-alive", "300"]
