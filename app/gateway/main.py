from fastapi import FastAPI, HTTPException, UploadFile, File, Header, Request, Response, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import hashlib
import os
import time
import httpx
from collections import defaultdict

app = FastAPI(title="Distributed Storage Gateway - Task 5")

METADATA_URL = os.getenv("METADATA_URL", "http://metadata:8000")
STORAGE_NODES = [
    "http://storage-node-1:8000",
    "http://storage-node-2:8000",
    "http://storage-node-3:8000",
    "http://storage-node-4:8000",
]

API_KEYS = {"test-key-123": "user1"}
request_counts = defaultdict(list)

def check_auth(x_api_key: str = Header(None)):
    if x_api_key and x_api_key in API_KEYS:
        return API_KEYS[x_api_key]
    return "anonymous"

def rate_limit(request: Request):
    ip = request.client.host
    now = time.time()
    request_counts[ip] = [t for t in request_counts[ip] if now - t < 60]
    if len(request_counts[ip]) >= 100:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    request_counts[ip].append(now)

buckets: Dict[str, dict] = {"default": {"name": "default", "created": time.time()}}
objects: Dict[str, dict] = {}

class BucketCreate(BaseModel):
    name: str

def get_target_nodes(chunk_hash: str, n=3) -> List[str]:
    h = int(chunk_hash[:8], 16)
    return [STORAGE_NODES[(h + i) % len(STORAGE_NODES)] for i in range(n)]

@app.get("/health")
def health():
    return {"status": "ok", "service": "gateway", "version": "task5"}

@app.get("/")
def root():
    return {"message": "Distributed Object-Tolerant Storage Framework - Gateway", "docs": "/docs"}

@app.post("/buckets")
def create_bucket(bucket: BucketCreate, x_api_key: str = Header(None), request: Request = None):
    rate_limit(request)
    check_auth(x_api_key)
    if bucket.name in buckets:
        raise HTTPException(status_code=409, detail="Bucket already exists")
    buckets[bucket.name] = {"name": bucket.name, "created": time.time()}
    return buckets[bucket.name]

@app.get("/buckets")
def list_buckets(x_api_key: str = Header(None), request: Request = None):
    rate_limit(request)
    return list(buckets.values())

@app.post("/objects/{bucket}/{key}")
async def upload_object(bucket: str, key: str, file: UploadFile = File(...), x_api_key: str = Header(None), request: Request = None):
    rate_limit(request)
    check_auth(x_api_key)
    if bucket not in buckets:
        raise HTTPException(status_code=404, detail="Bucket not found")
    data = await file.read()
    from app.common.chunking import chunk_fixed
    chunks = chunk_fixed(data)
    stored_hashes = []
    for chunk_hash, chunk_data in chunks:
        target_nodes = get_target_nodes(chunk_hash, n=3)
        success = 0
        async with httpx.AsyncClient() as client:
            for node_url in target_nodes:
                try:
                    resp = await client.put(f"{node_url}/chunks/{chunk_hash}", content=chunk_data, timeout=10.0)
                    if resp.status_code in [200, 201]:
                        success += 1
                except:
                    continue
        if success < 2:
            raise HTTPException(status_code=500, detail=f"Failed to store chunk {chunk_hash}")
        stored_hashes.append(chunk_hash)
    obj_id = f"{bucket}/{key}"
    objects[obj_id] = {
        "bucket": bucket,
        "key": key,
        "size": len(data),
        "chunk_hashes": stored_hashes,
        "tags": {},
        "created_at": time.time(),
        "version": 1
    }
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{METADATA_URL}/files",
                params={"file_id": obj_id, "bucket": bucket, "key": key, "size": len(data)},
                json=stored_hashes,
                timeout=3.0
            )
        except:
            pass
    return {"bucket": bucket, "key": key, "size": len(data), "chunks": len(stored_hashes), "hashes": stored_hashes}

@app.post("/upload")
async def upload_simple(file: UploadFile = File(...)):
    return await upload_object("default", file.filename, file)

@app.get("/objects/{bucket}/{key}")
async def download_object(bucket: str, key: str, request: Request, range: str = Header(None), x_api_key: str = Header(None)):
    rate_limit(request)
    obj_id = f"{bucket}/{key}"
    if obj_id not in objects:
        raise HTTPException(status_code=404, detail="Object not found")
    obj = objects[obj_id]
    async with httpx.AsyncClient() as client:
        full_data = b""
        for chunk_hash in obj["chunk_hashes"]:
            target_nodes = get_target_nodes(chunk_hash, n=3)
            chunk_data = None
            for node_url in target_nodes:
                try:
                    resp = await client.get(f"{node_url}/chunks/{chunk_hash}", timeout=5.0)
                    if resp.status_code == 200:
                        chunk_data = resp.content
                        break
                except:
                    continue
            if not chunk_data:
                raise HTTPException(status_code=500, detail=f"Chunk {chunk_hash} not available")
            full_data += chunk_data
    if range:
        try:
            range_val = range.replace("bytes=", "")
            start, end = range_val.split("-")
            start = int(start) if start else 0
            end = int(end) if end else len(full_data) - 1
            full_data = full_data[start:end+1]
            return Response(content=full_data, status_code=206, headers={"Content-Range": f"bytes {start}-{end}/{obj['size']}"})
        except:
            pass
    return StreamingResponse(iter([full_data]), media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename={key}"})

@app.get("/objects")
def list_objects(bucket: str = Query(None), prefix: str = Query(None), min_size: int = Query(None), max_size: int = Query(None), tag: str = Query(None), x_api_key: str = Header(None), request: Request = None):
    rate_limit(request)
    result = list(objects.values())
    if bucket:
        result = [o for o in result if o["bucket"] == bucket]
    if prefix:
        result = [o for o in result if o["key"].startswith(prefix)]
    if min_size is not None:
        result = [o for o in result if o["size"] >= min_size]
    if max_size is not None:
        result = [o for o in result if o["size"] <= max_size]
    return result

@app.delete("/objects/{bucket}/{key}")
def delete_object(bucket: str, key: str, x_api_key: str = Header(None), request: Request = None):
    rate_limit(request)
    obj_id = f"{bucket}/{key}"
    if obj_id not in objects:
        raise HTTPException(status_code=404, detail="Object not found")
    del objects[obj_id]
    return {"deleted": obj_id}

@app.get("/objects/{bucket}/{key}/metadata")
def get_metadata(bucket: str, key: str):
    obj_id = f"{bucket}/{key}"
    if obj_id not in objects:
        raise HTTPException(status_code=404, detail="Object not found")
    return objects[obj_id]

@app.get("/cluster/status")
async def cluster_status():
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{METADATA_URL}/nodes", timeout=3.0)
            nodes = r.json()
        except:
            nodes = []
        try:
            r2 = await client.get(f"{METADATA_URL}/chunks", timeout=3.0)
            chunks = r2.json()
        except:
            chunks = []
    alive = [n for n in nodes if n.get("status") == "alive"]
    return {
        "nodes": nodes,
        "total_nodes": len(nodes),
        "alive_nodes": len(alive),
        "failed_nodes": len(nodes) - len(alive),
        "total_chunks": len(chunks),
        "storage_nodes": STORAGE_NODES,
        "buckets": len(buckets),
        "objects": len(objects)
    }