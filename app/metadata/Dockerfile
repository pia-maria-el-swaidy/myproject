FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn psycopg2-binary elasticsearch httpx
COPY app/metadata/main.py /app/main.py
COPY app/common/ /app/app/common/
COPY app/placement/ /app/app/placement/
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]