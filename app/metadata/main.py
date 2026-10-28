from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import os
import time
from typing import Dict, List

app = FastAPI(title="Metadata Service")

nodes: Dict[str, dict] = {}
files: Dict[str, dict] = {}
chunks: Dict[str, dict] = {}  # hash -> {ref_count, size}

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/storage_meta")

def get_db():
    try:
        return psycopg2.connect(DB_URL)
    except:
        return None

@app.on_event("startup")
def init_db():
    conn = get_db()
    if not conn:
        print("DB not ready, using in-memory")
        return
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            node_id TEXT PRIMARY KEY,
            last_heartbeat FLOAT,
            free_space BIGINT,
            chunk_count INT,
            status TEXT
        );
        CREATE TABLE IF NOT EXISTS files (
            file_id TEXT PRIMARY KEY,
            bucket TEXT,
            key TEXT,
            size BIGINT,
            chunk_hashes TEXT[],
            created_at FLOAT
        );
        CREATE TABLE IF NOT EXISTS chunks (
            hash TEXT PRIMARY KEY,
            size BIGINT,
            ref_count INT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("PostgreSQL tables initialized")

class Heartbeat(BaseModel):
    node_id: str
    free_space: int = 0
    chunk_count: int = 0

@app.post("/heartbeat")
def heartbeat(hb: Heartbeat):
    nodes[hb.node_id] = {
        "node_id": hb.node_id,
        "free_space": hb.free_space,
        "chunk_count": hb.chunk_count,
        "last_heartbeat": time.time(),
        "status": "alive"
    }
    # Also try DB
    conn = get_db()
    if conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO nodes (node_id, last_heartbeat, free_space, chunk_count, status)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (node_id) DO UPDATE SET last_heartbeat=%s, free_space=%s, chunk_count=%s, status=%s
        """, (hb.node_id, time.time(), hb.free_space, hb.chunk_count, "alive",
              time.time(), hb.free_space, hb.chunk_count, "alive"))
        conn.commit()
        cur.close()
        conn.close()
    return {"status": "ok"}

@app.get("/nodes")
def list_nodes():

    now = time.time()
    for n in nodes.values():
        if now - n["last_heartbeat"] > 10:
            n["status"] = "failed"
    return list(nodes.values())

@app.get("/health")
def health():
    return {"status": "ok", "nodes": len(nodes)}

@app.get("/files")
def list_files():
    return list(files.values())

@app.post("/files")
def register_file(file_id: str, bucket: str, key: str, size: int, chunk_hashes: List[str]):

    for h in chunk_hashes:
        if h in chunks:
            chunks[h]["ref_count"] += 1
        else:
            chunks[h] = {"hash": h, "size": 0, "ref_count": 1}
    files[file_id] = {"file_id": file_id, "bucket": bucket, "key": key, "size": size, "chunk_hashes": chunk_hashes, "created_at": time.time()}
    return files[file_id]

@app.get("/chunks")
def list_chunks():
    return list(chunks.values())