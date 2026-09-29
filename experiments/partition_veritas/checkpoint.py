"""
Checkpoint emission for partition_veritas.

Consumes SKN-like state snapshots; does not modify SKN production path.
Uses SHA3-512 when available, falls back to SHA-256 for the experiment harness.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, Optional


def _hash_bytes(data: bytes) -> str:
    try:
        return hashlib.sha3_512(data).hexdigest()
    except AttributeError:
        return hashlib.sha256(data).hexdigest()


def emit_checkpoint(
    node_id: int,
    state: Dict[str, Any],
    *,
    prev_hash: Optional[str] = None,
    evidence_refs: Optional[list] = None,
    phase: str = "CONNECTED",
) -> Dict[str, Any]:
    """
    Build a verifiable checkpoint commitment.

    Structure mirrors the concept document but stays local to the experiment.
    """
    body = {
        "node_id": node_id,
        "state": state,
        "phase": phase,
        "prev_hash": prev_hash,
        "evidence_refs": evidence_refs or [],
        "timestamp": time.time(),
    }
    raw = json.dumps(body, sort_keys=True, default=str).encode("utf-8")
    digest = _hash_bytes(raw)
    return {
        "node_id": node_id,
        "digest": digest,
        "prev_hash": prev_hash,
        "payload": body,
        "payload_bytes": raw,
    }


def checkpoint_from_skn_node(node: Any, prev_hash: Optional[str] = None) -> Dict[str, Any]:
    """
    Adapter: extract a minimal state dict from an SKN node if present.
    Falls back to a synthetic snapshot so the experiment remains runnable
    without a live swarm.
    """
    state: Dict[str, Any] = {}
    node_id = getattr(node, "node_id", getattr(node, "id", 0))
    if hasattr(node, "pose"):
        pose = node.pose
        state["pose"] = list(pose) if hasattr(pose, "__iter__") else pose
    if hasattr(node, "vault") and hasattr(node.vault, "head"):
        state["vault_head"] = str(node.vault.head)
    elif hasattr(node, "evidence_vault"):
        state["vault_head"] = "present"
    if not state:
        state = {"synthetic": True, "node_id": int(node_id)}
    return emit_checkpoint(int(node_id), state, prev_hash=prev_hash)
