#!/usr/bin/env python3
"""
CLI entry for partition_veritas.

Experimental / unvalidated integration.
Does not modify production SKN semantics.

Usage (from repo root):
    python -m experiments.partition_veritas.run_experiment --seed 42 --nodes 8
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .adversary import run_adversarial_suite
from .checkpoint import emit_checkpoint
from .fragment_store import FragmentStore
from .metrics import build_evidence_bundle, compute_metrics, write_bundle
from .protocol import Phase, Protocol
from .recovery import attempt_recovery


def _git_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=Path(__file__).resolve().parents[2],
        )
        return out.decode().strip()
    except Exception:
        return "unknown"


def run(
    seed: int = 42,
    nodes: int = 8,
    replication_factor: int = 3,
    results_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    experiment_id = "partition_veritas_v0"
    results_dir = results_dir or Path(__file__).resolve().parent / "results"

    protocol = Protocol(node_count=nodes)
    store = FragmentStore(replication_factor=replication_factor)

    # --- 1. Connected operation: emit checkpoints for all nodes ---
    protocol.advance(Phase.CHECKPOINT_EMITTED)
    checkpoint_hashes: List[str] = []
    checkpoints: Dict[int, Dict[str, Any]] = {}
    for i in range(nodes):
        cp = emit_checkpoint(
            i,
            {"pose": [float(i), 0.0, 0.0, 0.0, 0.0, 0.0], "synthetic": True},
            phase="CONNECTED",
        )
        checkpoints[i] = cp
        checkpoint_hashes.append(cp["digest"])
        protocol.state.checkpoints[i] = cp

    # --- 2. Distribute fragments (boring majority copies) ---
    protocol.advance(Phase.FRAGMENTS_DISTRIBUTED)
    alive = list(range(nodes))
    for i in range(nodes):
        store.distribute(i, checkpoints[i]["payload_bytes"], alive)

    partition_schedule = {"step": "after_checkpoint", "type": "full_cut"}
    failure_schedule = {"kill_node": nodes - 1, "after": "partition"}

    # --- 3. Partition ---
    protocol.set_partitioned(True)

    # --- 4. Kill one node ---
    killed = nodes - 1
    protocol.kill_node(killed)
    survivors = sorted(protocol.state.alive)
    survivor = survivors[0]
    peer_for_forge = survivors[1] if len(survivors) > 1 else survivors[0]

    # --- 5–8. Adversarial suite (unauthorized, companion, forged, stale) ---
    protocol.advance(Phase.ADVERSARIAL)
    adv_log = run_adversarial_suite(
        protocol,
        store,
        killed_id=killed,
        survivor_id=survivor,
        peer_for_forge=peer_for_forge,
        stale_digest=checkpoint_hashes[0] if checkpoint_hashes else "none",
    )

    # --- 9. Reconstruct dead node (includes forged copy on one peer) ---
    protocol.advance(Phase.RECONSTRUCTING)
    recovery_results: List[Dict[str, Any]] = []
    known = set(checkpoint_hashes)

    # Attempt with forged material present → must not admit.
    r_forged = attempt_recovery(
        store,
        killed,
        protocol.state.delegated,
        known_digests=known,
        forged=True,
        stale=False,
    )
    recovery_results.append(r_forged)

    # Clean majority path (re-distribute original to clear forge for contrast).
    store.distribute(killed, checkpoints[killed]["payload_bytes"], survivors)
    r_clean = attempt_recovery(
        store,
        killed,
        protocol.state.delegated,
        known_digests=known,
        forged=False,
        stale=False,
    )
    # recovery_admit is outside A_delegated → still REFUSE (Recoverable ≠ Trusted).
    recovery_results.append(r_clean)

    reconstruction_hashes = [
        r.get("reconstruction", {}).get("digest", "none") for r in recovery_results
    ]

    # Soft residual monitor (placeholder; real constraint geometry can plug in).
    protocol.record_residual(0.0)

    # --- 10. Reconcile ---
    protocol.advance(Phase.RECONCILE)
    protocol.advance(Phase.DONE)

    metrics = compute_metrics(protocol, recovery_results)
    bundle = build_evidence_bundle(
        experiment_id=experiment_id,
        git_commit=_git_commit(),
        seed=seed,
        protocol=protocol,
        partition_schedule=partition_schedule,
        failure_schedule=failure_schedule,
        adversarial_schedule=adv_log,
        checkpoint_hashes=checkpoint_hashes,
        reconstruction_hashes=reconstruction_hashes,
        recovery_results=recovery_results,
        metrics=metrics,
    )
    path = write_bundle(bundle, results_dir)

    return {
        "bundle_path": str(path),
        "metrics": metrics,
        "any_violation": metrics["any_violation"],
        "final_digest": bundle["final_digest"],
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="partition_veritas research experiment (unvalidated integration)"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--nodes", type=int, default=8)
    parser.add_argument("--replication-factor", type=int, default=3)
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help="Directory for evidence bundles (default: experiments/partition_veritas/results)",
    )
    args = parser.parse_args(argv)

    result = run(
        seed=args.seed,
        nodes=args.nodes,
        replication_factor=args.replication_factor,
        results_dir=args.results_dir,
    )
    print(json.dumps({
        "status": "Experimental / unvalidated integration",
        "bundle_path": result["bundle_path"],
        "any_violation": result["any_violation"],
        "metrics": result["metrics"],
        "final_digest": result["final_digest"],
        "note": (
            "A violation means the registered protocol failed an invariant "
            "under the registered threat model. Zero violations means zero "
            "observed under these conditions only."
        ),
    }, indent=2))
    # Exit 0 even on violations — violations are data, not harness failure.
    return 0


if __name__ == "__main__":
    sys.exit(main())
