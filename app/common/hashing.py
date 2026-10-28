import hashlib
import bisect
from typing import List, Dict

class ConsistentHashRing:
    def __init__(self, nodes: List[str], virtual_nodes: int = 150):
        self.virtual_nodes = virtual_nodes
        self.ring: Dict[int, str] = {}
        self.sorted_keys: List[int] = []
        for node in nodes:
            self.add_node(node)

    def _hash(self, key: str) -> int:
        return int(hashlib.sha256(key.encode()).hexdigest(), 16)

    def add_node(self, node: str):
        for i in range(self.virtual_nodes):
            vnode_key = f"{node}#{i}"
            h = self._hash(vnode_key)
            self.ring[h] = node
            bisect.insort(self.sorted_keys, h)

    def remove_node(self, node: str):
        to_remove = [h for h, n in self.ring.items() if n == node]
        for h in to_remove:
            del self.ring[h]
            self.sorted_keys.remove(h)

    def get_nodes(self, chunk_hash: str, n: int = 3) -> List[str]:
        if not self.ring:
            return []
        h = self._hash(chunk_hash)
        idx = bisect.bisect(self.sorted_keys, h) % len(self.sorted_keys)
        result = []
        seen = set()
        i = idx
        while len(result) < n and len(seen) < len(self.ring):
            node = self.ring[self.sorted_keys[i % len(self.sorted_keys)]]
            if node not in seen:
                result.append(node)
                seen.add(node)
            i += 1
        return result