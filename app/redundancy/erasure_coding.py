from typing import List, Tuple
import hashlib

try:
    from zfec import Encoder, Decoder

    ZFEC_AVAILABLE = True
except ImportError:
    ZFEC_AVAILABLE = False
    print("zfec not available, using replication fallback for erasure coding")


class ErasureCodingManager:
    def __init__(self, k: int = 4, m: int = 2):
        self.k = k
        self.m = m
        self.total = k + m
        if ZFEC_AVAILABLE:
            self.encoder = Encoder(k, self.total)
            self.decoder = Decoder(k, self.total)

    def encode(self, data: bytes) -> List[Tuple[int, bytes]]:
        """Split data into k+m shards"""
        if not ZFEC_AVAILABLE:

            chunk_size = (len(data) + self.k - 1) // self.k
            shards = []
            for i in range(self.k):
                start = i * chunk_size
                end = min(start + chunk_size, len(data))
                shards.append((i, data[start:end]))

            for i in range(self.m):
                shards.append((self.k + i, shards[i % self.k][1]))
            return shards

        chunk_size = (len(data) + self.k - 1) // self.k
        padded = data.ljust(chunk_size * self.k, b'\0')
        blocks = [padded[i * chunk_size:(i + 1) * chunk_size] for i in range(self.k)]
        encoded = self.encoder.encode(blocks)
        return [(i, encoded[i]) for i in range(self.total)]

    def decode(self, shards: List[Tuple[int, bytes]], original_size: int) -> bytes:
        """Reconstruct from k shards"""
        if not ZFEC_AVAILABLE:

            shards_sorted = sorted(shards[:self.k], key=lambda x: x[0])
            data = b''.join([s[1] for s in shards_sorted])
            return data[:original_size]


        shard_dict = {idx: d for idx, d in shards}
        blocks = []
        indices = []
        for i in range(self.total):
            if i in shard_dict:
                blocks.append(shard_dict[i])
                indices.append(i)
            if len(blocks) == self.k:
                break
        if len(blocks) < self.k:
            raise Exception(f"Need {self.k} shards, got {len(blocks)}")
        decoded = self.decoder.decode(blocks, indices)
        data = b''.join(decoded)
        return data[:original_size]

    def storage_overhead(self) -> float:
        """EC overhead = (k+m)/k"""
        return self.total / self.k

    def can_reconstruct(self, available_shards: int) -> bool:
        return available_shards >= self.k