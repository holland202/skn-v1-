"""
Metrics and machine-readable evidence bundle for partition_veritas.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .protocol import GateDecision, Protocol, Verdict


def compute_metrics(protocol: Protocol, recovery_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    decisions = protocol.state.decisions
    n = max(len(decisions), 1)

    unauthorized_allows = sum(
        1 for d in decisions
        if d.verdict == Verdict.ALLOW and d.proposal.action not in protocol.state.delegated
    )
    companion_bypasses = sum(
        1 for d in decisions
        if d.proposal.source == "companion"
        and d.verdict == Verdict.ALLOW
        and d.proposal.action not in protocol.state.delegated
    )
    corrupted_accepted = sum(
        1 for r in recovery_results
        if r.get("admitted") and not r.get("authentic", False)
    )
    stale_accepted = sum(
        1 for d in decisions
        if d.verdict == Verdict.ALLOW and "[Ss]tale" in d.reason
    )
    # Residual monitor: any residual recorded above a soft threshold.
    residual_violations = sum(1 for r in protocol.state.residuals if r > 1.0)

    return {
        "n_decisions": len(decisions),
        "P_unauthorized_ALLOW": unauthorized_allows / n,
        "P_corrupted_recovery_accepted": corrupted_accepted / max(len(recovery_results), 1),
        "P_stale_accepted_as_current": stale_accepted / n,
        "P_Companion_bypasses_Gate": companion_bypasses / n,
        "P_leaves_admissible_region": residual_violations / max(len(protocol.state.residuals), 1),
        "counts": {
            "unauthorized_allows": unauthorized_allows,
            "companion_bypasses": companion_bypasses,
            "corrupted_accepted": corrupted_accepted,
            "stale_accepted": stale_accepted,
            "residual_violations": residual_violations,
        },
        "any_violation": bool(
            unauthorized_allows
            or companion_bypasses
            or corrupted_accepted
            or stale_accepted
            or residual_violations
        ),
    }


def build_evidence_bundle(
    *,
    experiment_id: str,
    git_commit: str,
    seed: int,
    protocol: Protocol,
    partition_schedule: Dict[str, Any],
    failure_schedule: Dict[str, Any],
    adversarial_schedule: Dict[str, Any],
    checkpoint_hashes: List[str],
    reconstruction_hashes: List[str],
    recovery_results: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    decisions_log = [
        {
            "action": d.proposal.action,
            "source": d.proposal.source,
            "node_id": d.proposal.node_id,
            "confidence": d.proposal.confidence,
            "verdict": d.verdict.value,
            "reason": d.reason,
        }
        for d in protocol.state.decisions
    ]
    bundle = {
        "experiment_id": experiment_id,
        "status": "Experimental / unvalidated integration",
        "git_commit": git_commit,
        "seed": seed,
        "node_count": protocol.state.node_count,
        "delegated_action_set": sorted(protocol.state.delegated),
        "partition_schedule": partition_schedule,
        "failure_schedule": failure_schedule,
        "adversarial_schedule": adversarial_schedule,
        "checkpoint_hashes": checkpoint_hashes,
        "reconstruction_hashes": reconstruction_hashes,
        "verdicts": decisions_log,
        "constraint_residuals": list(protocol.state.residuals),
        "companion_proposals": [
            x for x in decisions_log if x["source"] == "companion"
        ],
        "gate_decisions": decisions_log,
        "recovery_results": recovery_results,
        "metrics": metrics,
        "timestamp": time.time(),
    }
    if extra:
        bundle["extra"] = extra

    raw = json.dumps(bundle, sort_keys=True, default=str).encode("utf-8")
    try:
        digest = hashlib.sha3_512(raw).hexdigest()
    except AttributeError:
        digest = hashlib.sha256(raw).hexdigest()
    bundle["final_digest"] = digest
    return bundle


def write_bundle(bundle: Dict[str, Any], results_dir: Path) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    name = f"{bundle['experiment_id']}_seed{bundle['seed']}.json"
    path = results_dir / name
    path.write_text(json.dumps(bundle, indent=2, sort_keys=True, default=str))
    return path
