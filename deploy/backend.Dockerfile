FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
COPY backend/requirements.api.txt /app/backend/requirements.api.txt
RUN pip install --no-cache-dir -r /app/requirements.txt \
    && pip install --no-cache-dir -r /app/backend/requirements.api.txt

COPY . /app

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "300"]
