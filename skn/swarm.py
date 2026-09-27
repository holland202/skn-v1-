"""
skn/swarm.py — SKN-V1 SWARM CONSENSUS ENGINE
"""
import numpy as np
from .topology import betti
import logging
from typing import Dict, List, Optional, Tuple, Set
from .node import SKNV1_SovereignNode

logger = logging.getLogger("skn.swarm")


class SwarmGossipProtocol:
    """Natural Gradient Gossip consensus on SE(3)."""

    def __init__(self, eta: float = 0.08):
        self.eta = eta
        self.nodes: Dict[str, SKNV1_SovereignNode] = {}
        self.topology: Dict[str, List[str]] = {}
        self._gossip_steps: int = 0
        self._frp_count: int = 0

    def register_node(self, node: SKNV1_SovereignNode, neighbors: List[str]) -> None:
        self.nodes[node.node_id] = node
        self.topology[node.node_id] = neighbors

    def set_topology(self, adjacency: Dict[str, List[str]]) -> None:
        self.topology = {k: list(v) for k, v in adjacency.items()}

    def gossip_step(self, dt: float = 0.05) -> dict:
        if len(self.nodes) < 2:
            return {"consensus_error": 0.0, "beta_1": 0, "frp_triggered": False,
                    "step": self._gossip_steps}

        deltas: Dict[str, np.ndarray] = {}
        for nid, node in self.nodes.items():
            neighbors = self.topology.get(nid, [])
            if not neighbors:
                deltas[nid] = np.zeros(6, dtype=np.float32)
                continue
            G_inv = np.linalg.pinv(node.fisher_metric)
            grad = np.zeros(6, dtype=np.float32)
            for jid in neighbors:
                if jid not in self.nodes:
                    continue
                j_node = self.nodes[jid]
                kl_grad = node.pose - j_node.pose
                grad += G_inv @ kl_grad
            deltas[nid] = (-self.eta * grad * dt).astype(np.float32)

        for nid, delta in deltas.items():
            self.nodes[nid].pose += delta
            self.nodes[nid].velocity = delta / (dt + 1e-10)

        self._gossip_steps += 1
        beta_1 = self.compute_betti_one()
        frp_triggered = False
        if beta_1 > 0:
            frp_triggered = True
            self._frp_count += 1
            self._formation_reconfiguration_protocol()

        return {
            "consensus_error": self.consensus_error(),
            "beta_1": beta_1, "frp_triggered": frp_triggered,
            "step": self._gossip_steps, "n_nodes": len(self.nodes),
        }

    def run(self, n_steps: int, dt: float = 0.05, target_error: float = 0.01) -> List[dict]:
        history = []
        for _ in range(n_steps):
            status = self.gossip_step(dt)
            history.append(status)
            if status["consensus_error"] < target_error:
                break
        return history

    def consensus_error(self) -> float:
        poses = [n.pose for n in self.nodes.values()]
        N = len(poses)
        if N < 2:
            return 0.0
        total = sum(
            float(np.linalg.norm(poses[i] - poses[j]))
            for i in range(N) for j in range(i + 1, N)
        )
        return total / (N * (N - 1) / 2)

    def compute_betti_one(self, comm_range: float = 50.0) -> int:
        """b1 of the swarm's Vietoris-Rips complex at radius comm_range (skn.topology, K1).
        Before 2026-09-27 this returned E - V + C of the communication graph, which counts every triangle
        of a fully connected formation as a hole; that count is kept as skn.topology.graph_cycle_rank."""
        return betti(self._positions(), comm_range)[1]

    def compute_betti_zero(self, comm_range: float = 50.0) -> int:
        """b0: number of connected pieces at radius comm_range. Fragmentation is b0 > 1."""
        return betti(self._positions(), comm_range)[0]

    def _positions(self) -> np.ndarray:
        return np.array([n.pose[:3] for n in self.nodes.values()], dtype=float).reshape(-1, 3)

    def _formation_reconfiguration_protocol(self) -> None:
        nids = list(self.nodes.keys())
        degrees = {nid: len(self.topology.get(nid, [])) for nid in nids}
        for _ in range(20):
            if self.compute_betti_one() == 0:
                break
            sorted_nids = sorted(degrees, key=degrees.get, reverse=True)
            if len(sorted_nids) < 2:
                break
            a, b = sorted_nids[0], sorted_nids[1]
            if b in self.topology.get(a, []):
                self.topology[a].remove(b)
                degrees[a] -= 1
            if a in self.topology.get(b, []):
                self.topology[b].remove(a)
                degrees[b] -= 1

    def parallel_transport(self, source_id: str, target_id: str, state: np.ndarray) -> np.ndarray:
        if source_id not in self.nodes or target_id not in self.nodes:
            return state.copy()
        src_pose = self.nodes[source_id].pose
        tgt_pose = self.nodes[target_id].pose
        displacement = tgt_pose - src_pose
        dist = float(np.linalg.norm(displacement))
        if dist < 1e-8:
            return state.copy()
        A_mu = displacement / dist
        g = 0.1
        projection = float(np.dot(A_mu, state))
        transported = state + g * projection * A_mu
        return transported.astype(np.float32)

    def swarm_status(self) -> dict:
        node_statuses = {nid: node.node_status() for nid, node in self.nodes.items()}
        poses = np.array([n.pose for n in self.nodes.values()])
        centroid = poses.mean(axis=0) if len(poses) > 0 else np.zeros(6)
        return {
            "n_nodes": len(self.nodes), "gossip_steps": self._gossip_steps,
            "frp_events": self._frp_count, "consensus_error": self.consensus_error(),
            "beta_1": self.compute_betti_one(), "beta_0": self.compute_betti_zero(),
            "centroid": centroid.tolist(),
            "topology": {k: list(v) for k, v in self.topology.items()},
            "nodes": node_statuses,
        }
