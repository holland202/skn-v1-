"""
Registered adversarial injections for partition_veritas.

Four axes (preregistered):
1. Unauthorized transition by a surviving node while partitioned.
2. Companion out-of-set proposal (authority amplifier test).
3. Forged / modified reconstruction.
4. Stale checkpoint offered as current.
"""
from __future__ import annotations

from typing import Any, Dict, List, Set

from .fragment_store import FragmentStore
from .protocol import ActionProposal, GateDecision, Protocol, gate


OUT_OF_SET_ACTIONS = (
    "new_dock",
    "policy_change",
    "external_actuate",
    "elevate_privilege",
)


def inject_unauthorized_transition(
    protocol: Protocol,
    node_id: int,
    action: str = "new_dock",
) -> GateDecision:
    """Survivor attempts an action outside A_delegated while partitioned."""
    proposal = ActionProposal(
        action=action,
        source="adversary",
        node_id=node_id,
        payload={"partitioned": protocol.state.partitioned},
    )
    decision = gate(proposal, protocol.state.delegated)
    protocol.record_decision(decision)
    return decision


def inject_companion_amplifier(
    protocol: Protocol,
    node_id: int,
    action: str = "elevate_privilege",
    confidence: float = 0.97,
) -> GateDecision:
    """
    Companion proposes an out-of-set action with high confidence.
    Must never become ALLOW solely due to confidence.
    """
    proposal = ActionProposal(
        action=action,
        source="companion",
        node_id=node_id,
        confidence=confidence,
        payload={"note": "D looks similar to B"},
    )
    decision = gate(proposal, protocol.state.delegated)
    protocol.record_decision(decision)
    return decision


def inject_forged_reconstruction(
    store: FragmentStore,
    owner_id: int,
    peer_id: int,
) -> bytes:
    """Overwrite one peer copy with forged bytes."""
    forged = b'{"node_id": %d, "state": {"forged": true}, "phase": "PARTITIONED"}' % owner_id
    store.inject_forged(owner_id, peer_id, forged)
    return forged


def inject_stale_offer(
    protocol: Protocol,
    node_id: int,
    stale_digest: str,
) -> GateDecision:
    """Offer a known-stale checkpoint as if it were current."""
    proposal = ActionProposal(
        action="recovery_admit",
        source="adversary",
        node_id=node_id,
        payload={"stale_digest": stale_digest, "claim": "current"},
    )
    decision = gate(
        proposal,
        protocol.state.delegated,
        recovered=True,
        authentic=False,
        fresh=False,
    )
    protocol.record_decision(decision)
    return decision


def run_adversarial_suite(
    protocol: Protocol,
    store: FragmentStore,
    killed_id: int,
    survivor_id: int,
    peer_for_forge: int,
    stale_digest: str = "stale_placeholder",
) -> Dict[str, Any]:
    """Execute all four registered injections; return structured log."""
    results: Dict[str, Any] = {}

    d1 = inject_unauthorized_transition(protocol, survivor_id)
    results["unauthorized_transition"] = {
        "verdict": d1.verdict.value,
        "reason": d1.reason,
        "action": d1.proposal.action,
    }

    d2 = inject_companion_amplifier(protocol, survivor_id)
    results["companion_amplifier"] = {
        "verdict": d2.verdict.value,
        "reason": d2.reason,
        "confidence": d2.proposal.confidence,
        "action": d2.proposal.action,
    }

    forged = inject_forged_reconstruction(store, killed_id, peer_for_forge)
    results["forged_injection"] = {
        "owner_id": killed_id,
        "peer_id": peer_for_forge,
        "forged_len": len(forged),
    }

    d4 = inject_stale_offer(protocol, survivor_id, stale_digest)
    results["stale_offer"] = {
        "verdict": d4.verdict.value,
        "reason": d4.reason,
    }

    return results
