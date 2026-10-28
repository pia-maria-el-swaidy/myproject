import hashlib
from typing import List, Tuple

CHUNK_SIZE = 4 * 1024 * 1024

def chunk_fixed(data: bytes, chunk_size: int = CHUNK_SIZE) -> List[Tuple[str, bytes]]:
    chunks = []
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i+chunk_size]
        h = hashlib.sha256(chunk).hexdigest()
        chunks.append((h, chunk))
    return chunks

def chunk_fastcdc(data: bytes, min_size=2*1024*1024, avg_size=4*1024*1024, max_size=8*1024*1024) -> List[Tuple[str, bytes]]:

    chunks = []
    start = 0

    while start < len(data):
        end = min(start + avg_size, len(data))
        if end < len(data):

            window = data[max(start+min_size, start):min(start+max_size, len(data))]

            for j in range(len(window)):
                if window[j] == 0 and j > 0:
                    end = start + min_size + j
                    break
        chunk = data[start:end]
        h = hashlib.sha256(chunk).hexdigest()
        chunks.append((h, chunk))
        start = end
    return chunks

def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()