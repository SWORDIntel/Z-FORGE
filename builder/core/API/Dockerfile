# Dockerfile for ARCHITECT Gemini Bridge v1.1
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
ENV GEMINI_API_KEY=""
ENV BRIDGE_API_KEY=""
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
