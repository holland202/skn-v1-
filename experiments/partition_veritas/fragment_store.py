"""
Boring majority replication for partition_veritas.

Deliberately not Reed-Solomon. Experiment #1 tests authority/evidence
invariants, not optimal distributed storage.

Each checkpoint is stored in full on a configured set of peer nodes.
Reconstruction requires a majority of identical copies.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from typing import Dict, List, Optional, Tuple


def _digest(blob: bytes) -> str:
    try:
        return hashlib.sha3_512(blob).hexdigest()
    except AttributeError:
        return hashlib.sha256(blob).hexdigest()


class FragmentStore:
    """
    node_id -> { peer_id -> raw checkpoint bytes }
    """

    def __init__(self, replication_factor: int = 3) -> None:
        self.replication_factor = max(1, replication_factor)
        self._store: Dict[int, Dict[int, bytes]] = {}

    def distribute(
        self,
        owner_id: int,
        payload_bytes: bytes,
        alive_peers: List[int],
    ) -> List[int]:
        """
        Copy full payload to up to replication_factor distinct peers
        (excluding owner). Returns the peer ids that received a copy.
        """
        peers = [p for p in alive_peers if p != owner_id][: self.replication_factor]
        if owner_id not in self._store:
            self._store[owner_id] = {}
        # Owner also keeps a local copy under its own id for bookkeeping.
        self._store[owner_id][owner_id] = payload_bytes
        for p in peers:
            if p not in self._store:
                self._store[p] = {}
            self._store[p][owner_id] = payload_bytes
            self._store[owner_id][p] = payload_bytes
        return peers

    def collect_copies(self, owner_id: int) -> List[bytes]:
        """All known copies of owner's checkpoint across the store."""
        copies: List[bytes] = []
        for peer_map in self._store.values():
            if owner_id in peer_map:
                copies.append(peer_map[owner_id])
        return copies

    def reconstruct_majority(self, owner_id: int) -> Tuple[Optional[bytes], Dict[str, object]]:
        """
        Majority vote on identical blobs.

        Returns (payload_or_None, meta) where meta records counts and
        whether a majority was reached. Reconstruction success does NOT
        imply authenticity — caller must still run Veritas verification.
        """
        copies = self.collect_copies(owner_id)
        if not copies:
            return None, {"copies": 0, "majority": False, "reason": "no_copies"}

        counts: Counter = Counter(_digest(c) for c in copies)
        best_digest, best_count = counts.most_common(1)[0]
        majority_needed = (len(copies) // 2) + 1
        if best_count < majority_needed:
            return None, {
                "copies": len(copies),
                "majority": False,
                "best_count": best_count,
                "needed": majority_needed,
                "reason": "no_majority",
            }

        # Return one of the matching blobs.
        for c in copies:
            if _digest(c) == best_digest:
                return c, {
                    "copies": len(copies),
                    "majority": True,
                    "best_count": best_count,
                    "digest": best_digest,
                    "reason": "majority_match",
                }
        return None, {"copies": len(copies), "majority": False, "reason": "internal_error"}

    def inject_forged(self, owner_id: int, peer_id: int, forged: bytes) -> None:
        """Adversary helper: overwrite one peer's copy."""
        if peer_id not in self._store:
            self._store[peer_id] = {}
        self._store[peer_id][owner_id] = forged
