import os
import hashlib
import shutil
import threading
import time
import psutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import FileResponse
import httpx

app = FastAPI(title="Storage Node")

DATA_DIR = os.getenv("DATA_DIR", "/data")
NODE_ID = os.getenv("NODE_ID", "node-1")
METADATA_URL = os.getenv("METADATA_URL", "http://metadata:8000/heartbeat")

os.makedirs(DATA_DIR, exist_ok=True)


def compute_sha256(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


@app.put("/chunks/{chunk_hash}")
async def put_chunk(chunk_hash: str, file: UploadFile = File(...)):
    # Save temp file
    temp_path = os.path.join(DATA_DIR, f".tmp_{chunk_hash}")
    final_path = os.path.join(DATA_DIR, chunk_hash)

    if len(chunk_hash) != 64:
        raise HTTPException(status_code=400, detail="Invalid SHA-256 hash length")

    try:
        with open(temp_path, "wb") as out:
            shutil.copyfileobj(file.file, out)

        # Verify hash
        actual_hash = compute_sha256(temp_path)
        if actual_hash != chunk_hash:
            os.remove(temp_path)
            raise HTTPException(status_code=400, detail=f"Hash mismatch: expected {chunk_hash}, got {actual_hash}")

        if not os.path.exists(final_path):
            shutil.move(temp_path, final_path)
        else:
            os.remove(temp_path)

        return {"status": "stored", "hash": chunk_hash, "node_id": NODE_ID}
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e


@app.get("/chunks/{chunk_hash}")
async def get_chunk(chunk_hash: str):
    file_path = os.path.join(DATA_DIR, chunk_hash)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Chunk not found")

    actual_hash = compute_sha256(file_path)
    if actual_hash != chunk_hash:
        # Corrupted chunk
        raise HTTPException(status_code=500, detail=f"Chunk corrupted: hash mismatch, possible bit-rot")

    return FileResponse(file_path)


@app.head("/chunks/{chunk_hash}")
async def head_chunk(chunk_hash: str):
    file_path = os.path.join(DATA_DIR, chunk_hash)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404)
    size = os.path.getsize(file_path)
    return Response(headers={"Content-Length": str(size), "X-Chunk-Hash": chunk_hash})


@app.delete("/chunks/{chunk_hash}")
async def delete_chunk(chunk_hash: str):
    file_path = os.path.join(DATA_DIR, chunk_hash)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404)
    os.remove(file_path)
    return {"status": "deleted", "hash": chunk_hash}


@app.get("/health")
async def health():
    usage = psutil.disk_usage(DATA_DIR)
    files = [f for f in os.listdir(DATA_DIR) if not f.startswith(".tmp_")]
    return {
        "node_id": NODE_ID,
        "status": "healthy",
        "free_space": usage.free,
        "total_space": usage.total,
        "chunk_count": len(files)
    }


@app.get("/chunks")
async def list_chunks():
    files = [f for f in os.listdir(DATA_DIR) if len(f) == 64]
    return {"node_id": NODE_ID, "chunks": files, "count": len(files)}


def heartbeat_loop():
    while True:
        try:
            usage = psutil.disk_usage(DATA_DIR)
            chunk_count = len([f for f in os.listdir(DATA_DIR) if len(f) == 64])
            payload = {
                "node_id": NODE_ID,
                "free_space": usage.free,
                "chunk_count": chunk_count,
                "status": "healthy"
            }

            try:
                httpx.post(METADATA_URL, json=payload, timeout=2)
            except:
                pass
        except Exception as e:
            print(f"Heartbeat error: {e}")
        time.sleep(3)


threading.Thread(target=heartbeat_loop, daemon=True).start()