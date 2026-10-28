FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn httpx psutil python-multipart
COPY app/storage_node/main.py /app/main.py
RUN mkdir -p /data
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]