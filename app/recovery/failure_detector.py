import time
from typing import Dict, List


class FailureDetector:
    def __init__(self, heartbeat_timeout: float = 10.0):
        self.timeout = heartbeat_timeout
        self.nodes: Dict[str, float] = {}

    def heartbeat(self, node_id: str):
        self.nodes[node_id] = time.time()

    def get_failed_nodes(self) -> List[str]:
        now = time.time()
        failed = []
        for node_id, last in self.nodes.items():
            if now - last > self.timeout:
                failed.append(node_id)
        return failed

    def get_alive_nodes(self) -> List[str]:
        now = time.time()
        alive = []
        for node_id, last in self.nodes.items():
            if now - last <= self.timeout:
                alive.append(node_id)
        return alive