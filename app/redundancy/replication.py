import hashlib
from typing import List, Dict
import httpx


class ReplicationManager:
    def __init__(self, n: int = 3, w: int = 2, r: int = 2):
        self.N = n
        self.W = w
        self.R = r  
        assert w + r > n, "W+R must > N for quorum"

    async def write_chunk(self, chunk_hash: str, data: bytes, target_nodes: List[str]) -> int:
        """Write to N nodes, return success count, need W for success"""
        success = 0
        async with httpx.AsyncClient() as client:
            for node_url in target_nodes[:self.N]:
                try:
                    resp = await client.put(
                        f"{node_url}/chunks/{chunk_hash}",
                        content=data,
                        timeout=5.0
                    )
                    if resp.status_code in [200, 201]:
                        success += 1
                except Exception as e:
                    print(f"Write failed to {node_url}: {e}")
        return success

    async def read_chunk(self, chunk_hash: str, target_nodes: List[str]) -> bytes:
        """Read from nodes, need R successes, return first valid"""
        successes = []
        async with httpx.AsyncClient() as client:
            for node_url in target_nodes[:self.N]:
                try:
                    resp = await client.get(f"{node_url}/chunks/{chunk_hash}", timeout=5.0)
                    if resp.status_code == 200:
                        # Verify hash
                        actual = hashlib.sha256(resp.content).hexdigest()
                        if actual == chunk_hash:
                            successes.append(resp.content)
                            if len(successes) >= self.R:
                                return successes[0]
                except:
                    continue
        if successes:
            return successes[0]
        raise Exception(f"Failed to read chunk {chunk_hash}, quorum {self.R} not reached")

    def storage_overhead(self) -> float:
        """Replication overhead = N"""
        return float(self.N)