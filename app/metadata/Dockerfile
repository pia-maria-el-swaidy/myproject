FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn psycopg2-binary elasticsearch httpx
COPY metadata/main.py /app/main.py
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]