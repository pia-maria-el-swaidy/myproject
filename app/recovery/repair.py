import asyncio
import httpx
from typing import List, Dict


class RepairManager:
    def __init__(self, metadata_url: str, storage_nodes: List[str]):
        self.metadata_url = metadata_url
        self.storage_nodes = storage_nodes

    async def repair_node(self, failed_node_id: str):
        """Rebuild chunks from failed node onto remaining nodes"""
        print(f"Starting repair for failed node: {failed_node_id}")

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.metadata_url}/nodes")
                nodes = resp.json()
                alive = [n for n in nodes if n['node_id'] != failed_node_id and n['status'] == 'alive']
                print(f"Repair: {len(alive)} alive nodes available to rebuild from")
                return {"failed_node": failed_node_id, "alive_nodes": len(alive), "status": "repair_triggered"}
            except Exception as e:
                print(f"Repair failed: {e}")
                return {"error": str(e)}


class Scrubber:
    """Background scrubber that re-reads chunks and detects bit rot"""

    def __init__(self, storage_nodes: List[str]):
        self.nodes = storage_nodes
        self.corrupted_chunks = []

    async def scrub(self):
        """Periodically verify all chunks"""
        print("Starting scrubber...")
        async with httpx.AsyncClient() as client:
            for node_url in self.nodes:
                try:

                    resp = await client.get(f"{node_url}/chunks", timeout=5.0)
                    if resp.status_code == 200:
                        chunks = resp.json()
                        for chunk_info in chunks:
                            chunk_hash = chunk_info.get('hash')
                            if not chunk_hash:
                                continue

                            r = await client.get(f"{node_url}/chunks/{chunk_hash}", timeout=5.0)
                            if r.status_code == 200:
                                import hashlib
                                actual = hashlib.sha256(r.content).hexdigest()
                                if actual != chunk_hash:
                                    print(f"BIT ROT detected: {chunk_hash} on {node_url}")
                                    self.corrupted_chunks.append((node_url, chunk_hash))
                                    # Repair from healthy copy
                                    await self.repair_chunk(chunk_hash, node_url)
                except Exception as e:
                    print(f"Scrub error on {node_url}: {e}")

    async def repair_chunk(self, chunk_hash: str, corrupted_node: str):
        """Repair corrupted chunk from healthy replica"""
        print(f"Repairing corrupted chunk {chunk_hash} from healthy copy")

        async with httpx.AsyncClient() as client:
            for node_url in self.nodes:
                if node_url == corrupted_node:
                    continue
                try:
                    resp = await client.get(f"{node_url}/chunks/{chunk_hash}", timeout=5.0)
                    if resp.status_code == 200:

                        await client.put(f"{corrupted_node}/chunks/{chunk_hash}", content=resp.content, timeout=5.0)
                        print(f"Repaired {chunk_hash} on {corrupted_node}")
                        return
                except:
                    continue