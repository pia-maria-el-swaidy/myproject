FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn httpx python-multipart
COPY app/gateway/main.py /app/main.py
COPY app/common/ /app/app/common/
COPY app/placement/ /app/app/placement/
COPY app/redundancy/ /app/app/redundancy/
COPY app/recovery/ /app/app/recovery/
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]