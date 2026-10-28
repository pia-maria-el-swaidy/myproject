from app.common.hashing import ConsistentHashRing


class PlacementService:
    def __init__(self):
        self.ring = ConsistentHashRing([])

    def update_nodes(self, alive_nodes: list):
        self.ring = ConsistentHashRing(alive_nodes, virtual_nodes=150)

    def place_chunk(self, chunk_hash: str, replication_factor: int = 3):
        return self.ring.get_nodes(chunk_hash, n=replication_factor)