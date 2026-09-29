"""
partition_veritas protocol — experimental / unvalidated integration.

Does not modify production SKN semantics.
Consumes existing SKN interfaces via adapter; injects adversaries;
requires independent verification of recovered state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class Phase(str, Enum):
    CONNECTED = "CONNECTED"
    CHECKPOINT_EMITTED = "CHECKPOINT_EMITTED"
    FRAGMENTS_DISTRIBUTED = "FRAGMENTS_DISTRIBUTED"
    PARTITIONED = "PARTITIONED"
    NODE_KILLED = "NODE_KILLED"
    ADVERSARIAL = "ADVERSARIAL"
    RECONSTRUCTING = "RECONSTRUCTING"
    RECONCILE = "RECONCILE"
    DONE = "DONE"


class Verdict(str, Enum):
    ALLOW = "ALLOW"
    DEFER = "DEFER"
    REFUSE = "REFUSE"
    NEVER_WIRED = "NEVER_WIRED"


# Default delegated set: formation maintenance + topology reporting only.
DEFAULT_DELEGATED: Set[str] = {
    "formation_maintain",
    "topology_report",
    "vault_attest",
}


@dataclass
class ActionProposal:
    action: str
    source: str  # "node" | "companion" | "adversary" | "recovery"
    node_id: int
    payload: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0


@dataclass
class GateDecision:
    proposal: ActionProposal
    verdict: Verdict
    reason: str
    delegated_set: Set[str]


@dataclass
class ProtocolState:
    phase: Phase = Phase.CONNECTED
    node_count: int = 8
    alive: Set[int] = field(default_factory=set)
    partitioned: bool = False
    delegated: Set[str] = field(default_factory=lambda: set(DEFAULT_DELEGATED))
    checkpoints: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    fragments: Dict[int, Dict[int, bytes]] = field(default_factory=dict)  # node -> peer -> blob
    decisions: List[GateDecision] = field(default_factory=list)
    residuals: List[float] = field(default_factory=list)
    killed: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.alive:
            self.alive = set(range(self.node_count))


def gate(
    proposal: ActionProposal,
    delegated: Set[str],
    *,
    recovered: bool = False,
    authentic: bool = False,
    fresh: bool = True,
) -> GateDecision:
    """
    Minimal Veritas-style gate for the experiment.

    Rules (fail-closed):
    - Companion / adversary cannot enlarge the authorized set.
    - Recovered state is never automatically trusted.
    - Only actions in delegated set may be ALLOW under partition.
    """
    if proposal.source == "companion":
        # Model-authority separation: confidence never creates ALLOW for out-of-set.
        if proposal.action not in delegated:
            return GateDecision(
                proposal, Verdict.REFUSE,
                "Companion cannot enlarge authorized set",
                set(delegated),
            )
        # Even in-set proposals from Companion are DEFER when recovered/unauthenticated.
        if recovered and not authentic:
            return GateDecision(
                proposal, Verdict.DEFER,
                "Recovered proposal requires independent authentication",
                set(delegated),
            )

    if recovered and not authentic:
        return GateDecision(
            proposal, Verdict.REFUSE,
            "Recoverable ≠ Trusted: reconstruction alone is insufficient",
            set(delegated),
        )

    if not fresh:
        return GateDecision(
            proposal, Verdict.REFUSE,
            "Stale checkpoint cannot be treated as current",
            set(delegated),
        )

    if proposal.action not in delegated:
        return GateDecision(
            proposal, Verdict.REFUSE,
            f"Action {proposal.action!r} outside A_delegated",
            set(delegated),
        )

    return GateDecision(
        proposal, Verdict.ALLOW,
        "Within delegated set; evidence conditions satisfied",
        set(delegated),
    )


class Protocol:
    """
    Orchestrates the registered adversarial schedule.
    Adapters inject SKN state; this class never mutates SKN internals.
    """

    def __init__(
        self,
        node_count: int = 8,
        delegated: Optional[Set[str]] = None,
        skn_adapter: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.state = ProtocolState(
            node_count=node_count,
            delegated=set(delegated) if delegated else set(DEFAULT_DELEGATED),
        )
        self.skn_adapter = skn_adapter  # optional; experiment works without live SKN

    def advance(self, phase: Phase) -> None:
        self.state.phase = phase

    def record_decision(self, decision: GateDecision) -> None:
        self.state.decisions.append(decision)

    def record_residual(self, r: float) -> None:
        self.state.residuals.append(float(r))

    def kill_node(self, node_id: int) -> None:
        self.state.alive.discard(node_id)
        self.state.killed = node_id
        self.state.phase = Phase.NODE_KILLED

    def set_partitioned(self, value: bool = True) -> None:
        self.state.partitioned = value
        if value:
            self.state.phase = Phase.PARTITIONED
