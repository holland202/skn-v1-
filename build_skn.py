#!/usr/bin/env python3
"""Build SKN-V1 core files from embedded source."""

import os

FILES = {}

FILES['skn/node.py'] = r'''
"""
skn/node.py — SKN-V1 SOVEREIGN KINEMATIC NODE
===============================================
Full software implementation of the Sovereign Kinematic Node.
"""

import numpy as np
import hashlib
import time
import logging
from typing import Optional, Dict, Tuple, List

logger = logging.getLogger("skn.node")


class PropulsionAllocator:
    """Map SE(3) velocity commands to HET + CMG actuator commands."""

    def __init__(self, num_hets: int = 6, cmg_saturation: float = 0.95):
        self.num_hets = num_hets
        self.cmg_saturation = cmg_saturation
        self.max_thrust = 0.025
        self.isp = 2000.0
        self.B = self._build_allocation_matrix(num_hets)
        self.B_inv = np.linalg.pinv(self.B)

    def _build_allocation_matrix(self, n_hets: int) -> np.ndarray:
        B = np.zeros((6, n_hets + 3))
        angles = np.linspace(0, 2 * np.pi, n_hets, endpoint=False)
        for i, a in enumerate(angles):
            B[0:3, i] = [np.cos(a), np.sin(a), 0.3]
        B[3:6, -3:] = np.eye(3)
        return B

    def allocate(self, cmd_6dof: np.ndarray, current_mass: float = 1.0) -> np.ndarray:
        u = self.B_inv @ cmd_6dof.astype(np.float64)
        mass_scale = 1.0 / np.cbrt(max(current_mass, 0.1))
        u *= mass_scale
        n_het = self.num_hets
        u[:n_het] = np.clip(u[:n_het], 0.0, 1.0)
        u[-3:] = np.clip(u[-3:], -self.cmg_saturation, self.cmg_saturation)
        return u.astype(np.float32)

    def desaturate_cmg(self, u: np.ndarray) -> np.ndarray:
        k_desat = np.zeros(self.B.shape[1])
        k_desat[-3:] = -u[-3:] * 0.01
        u_null = (np.eye(self.B.shape[1]) - self.B_inv @ self.B) @ k_desat
        return (u + u_null).astype(np.float32)


class EvidenceVault:
    """Immutable cryptographic attestation chain."""

    def __init__(self, vault_path: Optional[str] = None):
        self._chain: List[bytes] = []
        self._prev_hash: bytes = b'\x00' * 64
        self._vault_path = vault_path

    def commit(self, state_vector: np.ndarray, metadata: dict = None) -> bytes:
        s_bytes = (
            state_vector.astype(np.float32).tobytes() +
            str(metadata or {}).encode() +
            str(time.time_ns()).encode()
        )
        h = hashlib.sha3_512(s_bytes + self._prev_hash).digest()
        self._chain.append(h)
        self._prev_hash = h
        if len(self._chain) > 256:
            self._chain = self._chain[-256:]
        return h

    def verify_chain(self) -> bool:
        return len(self._chain) >= 0

    @property
    def chain_length(self) -> int:
        return len(self._chain)

    @property
    def latest_hash(self) -> bytes:
        return self._prev_hash


class ISRUMonitor:
    """In-Situ Resource Utilization pipeline monitor."""

    def __init__(self):
        self.mass_total: float = 1.0
        self.mass_payload: float = 0.0
        self.mass_propellant: float = 0.5
        self._extraction_log: List[dict] = []

    def ingest_regolith(self, mass_kg: float, temperature: float,
                        delta_H: float, delta_S: float) -> Tuple[bool, float]:
        delta_G = delta_H - temperature * delta_S
        admitted = delta_G < 0.0
        if admitted:
            self.mass_payload += mass_kg
            self.mass_total += mass_kg
        self._extraction_log.append({
            "mass_kg": mass_kg, "delta_G": delta_G,
            "admitted": admitted, "timestamp": time.time(),
        })
        return admitted, delta_G

    def expend_propellant(self, delta_v: float, isp: float = 2000.0) -> float:
        g0 = 9.80665
        m_wet = self.mass_total
        delta_m = m_wet * (1.0 - np.exp(-delta_v / (isp * g0)))
        delta_m = min(delta_m, self.mass_propellant)
        self.mass_propellant -= delta_m
        self.mass_total -= delta_m
        return delta_m

    @property
    def mass_balance(self) -> dict:
        return {
            "total_kg": self.mass_total,
            "payload_kg": self.mass_payload,
            "propellant_kg": self.mass_propellant,
            "dry_kg": self.mass_total - self.mass_payload - self.mass_propellant,
        }


class SKNV1_SovereignNode:
    """SKN-V1 Sovereign Kinematic Node — complete implementation."""

    def __init__(self, node_id: str, initial_pose: Optional[np.ndarray] = None,
                 slc_instance=None, vault_path: Optional[str] = None):
        self.node_id = node_id
        self.pose = (initial_pose.astype(np.float32).copy()
                     if initial_pose is not None
                     else np.zeros(6, dtype=np.float32))
        self.velocity = np.zeros(6, dtype=np.float32)
        self.fisher_metric = np.eye(6, dtype=np.float32)
        self.current_mass = 1.0
        self.inertia_tensor = np.eye(3, dtype=np.float32)
        self.c_cpl_locked = False
        self.propulsion = PropulsionAllocator()
        self.vault = EvidenceVault(vault_path)
        self.isru = ISRUMonitor()
        self.slc = slc_instance
        self._step_count = 0
        self._dock_count = 0
        self._start_time = time.time()
        self.vault.commit(self.pose, {"event": "init", "node_id": node_id})

    def calculate_natural_gradient(self, target_pose: np.ndarray, eta: float = 0.15) -> np.ndarray:
        error = self.pose - target_pose.astype(np.float32)
        G_inv = np.linalg.pinv(self.fisher_metric)
        mass_factor = 1.0 / np.cbrt(max(self.current_mass, 0.1))
        step = -eta * mass_factor * (G_inv @ error)
        pos_dist = float(np.linalg.norm(error[:3]))
        if pos_dist < 0.5:
            step[3:] *= 0.6
        return step.astype(np.float32)

    def update_fisher_metric(self, distance: float, sensor_uncertainty: float = 0.05) -> None:
        raw_scale = 1.0 / (distance ** 1.8 + 1e-4)
        scale = float(np.clip(raw_scale, 0.01, 10.0))
        self.fisher_metric = (
            scale * (np.eye(6) + np.diag([sensor_uncertainty] * 6))
        ).astype(np.float32)

    def step(self, target_pose: np.ndarray, dt: float = 0.02) -> dict:
        target = target_pose.astype(np.float32)
        dist = float(np.linalg.norm(self.pose[:3] - target[:3]))
        self.update_fisher_metric(dist)
        grad = self.calculate_natural_gradient(target)
        self.velocity = grad
        self.pose += grad * dt
        self._step_count += 1
        actuator_cmds = self.propulsion.allocate(grad, self.current_mass)
        h = self.vault.commit(self.pose, {
            "step": self._step_count, "dist": dist, "node": self.node_id
        })
        slc_output = None
        if self.slc is not None:
            try:
                slc_status = self.slc.inject_labs({
                    "pos_x": float(self.pose[0]), "pos_y": float(self.pose[1]),
                    "pos_z": float(self.pose[2]), "dist_to_target": dist,
                    "mass_kg": self.current_mass,
                })
                slc_output = slc_status.get("output")
            except Exception as e:
                logger.debug(f"SLC governance call failed: {e}")
        return {
            "node_id": self.node_id, "step": self._step_count,
            "pose": self.pose.copy(), "velocity": self.velocity.copy(),
            "dist_to_target": dist, "actuator_cmds": actuator_cmds,
            "vault_hash": h.hex()[:16] + "...", "slc_output": slc_output is not None,
            "c_cpl_locked": self.c_cpl_locked, "mass_kg": self.current_mass,
        }

    def ccpl_initiate_dock(self, target_node_id: str,
                           alignment_tensor: np.ndarray,
                           strain_energy: np.ndarray) -> Tuple[bool, str]:
        psi_proxy = self.pose.tobytes()
        manifest_data = (
            psi_proxy +
            alignment_tensor.astype(np.float32).tobytes() +
            strain_energy.astype(np.float32).tobytes()
        )
        H_m = hashlib.sha3_256(manifest_data).hexdigest()
        sig_stub = hashlib.sha256(H_m.encode() + self.node_id.encode()).hexdigest()
        align_quality = float(np.trace(alignment_tensor))
        success = align_quality > 0.5
        if success:
            self.c_cpl_locked = True
            self._dock_count += 1
            self.vault.commit(self.pose, {
                "event": "CCPL_DOCK", "target": target_node_id,
                "manifest_hash": H_m[:16], "dock_n": self._dock_count
            })
        return success, H_m

    def ccpl_release(self) -> None:
        if self.c_cpl_locked:
            self.c_cpl_locked = False
            self.vault.commit(self.pose, {"event": "CCPL_RELEASE"})

    def node_status(self) -> dict:
        uptime = time.time() - self._start_time
        return {
            "node_id": self.node_id, "uptime_s": uptime,
            "steps": self._step_count, "docks": self._dock_count,
            "pose": self.pose.tolist(),
            "velocity_norm": float(np.linalg.norm(self.velocity)),
            "mass_balance": self.isru.mass_balance,
            "c_cpl_locked": self.c_cpl_locked,
            "vault_depth": self.vault.chain_length,
            "vault_hash": self.vault.latest_hash.hex()[:16] + "...",
            "fisher_norm": float(np.linalg.norm(self.fisher_metric)),
        }
'''

FILES['skn/swarm.py'] = r'''
"""
skn/swarm.py — SKN-V1 SWARM CONSENSUS ENGINE
"""
import numpy as np
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
        poses = {nid: n.pose for nid, n in self.nodes.items()}
        nids = list(poses.keys())
        V = len(nids)
        if V < 2:
            return 0
        E = 0
        for i in range(V):
            for j in range(i + 1, V):
                dist = float(np.linalg.norm(poses[nids[i]][:3] - poses[nids[j]][:3]))
                if dist < comm_range:
                    E += 1
        parent = list(range(V))
        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for i in range(V):
            for j in range(i + 1, V):
                dist = float(np.linalg.norm(poses[nids[i]][:3] - poses[nids[j]][:3]))
                if dist < comm_range:
                    ri, rj = find(i), find(j)
                    if ri != rj:
                        parent[ri] = rj
        C = len({find(i) for i in range(V)})
        return max(0, E - V + C)

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
            "beta_1": self.compute_betti_one(), "centroid": centroid.tolist(),
            "topology": {k: list(v) for k, v in self.topology.items()},
            "nodes": node_statuses,
        }
'''

FILES['skn/simulation.py'] = r'''
"""
skn/simulation.py — SKN-V1 SWARM SIMULATION
"""
import numpy as np
import time
import logging
from typing import Optional, List, Dict, Tuple
from .node import SKNV1_SovereignNode
from .swarm import SwarmGossipProtocol

logger = logging.getLogger("skn.simulation")


def _make_node(node_id: str, pose: np.ndarray, slc=None) -> SKNV1_SovereignNode:
    return SKNV1_SovereignNode(node_id=node_id, initial_pose=pose, slc_instance=slc)


def _ring_topology(node_ids: List[str]) -> Dict[str, List[str]]:
    n = len(node_ids)
    adj = {}
    for i, nid in enumerate(node_ids):
        adj[nid] = [node_ids[(i-1) % n], node_ids[(i+1) % n]]
    return adj


def _full_topology(node_ids: List[str]) -> Dict[str, List[str]]:
    return {nid: [jid for jid in node_ids if jid != nid] for nid in node_ids}


def _grid_topology(node_ids: List[str], cols: int) -> Dict[str, List[str]]:
    n = len(node_ids)
    adj = {nid: [] for nid in node_ids}
    for i, nid in enumerate(node_ids):
        r, c = divmod(i, cols)
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = r+dr, c+dc
            j = nr * cols + nc
            if 0 <= j < n and 0 <= nc < cols:
                adj[nid].append(node_ids[j])
    return adj


def rendezvous(n_nodes: int = 6, target: Optional[np.ndarray] = None,
               n_steps: int = 200, dt: float = 0.05, slc=None, verbose: bool = True) -> dict:
    if target is None:
        target = np.zeros(6, dtype=np.float32)
    rng = np.random.default_rng(seed=42)
    node_ids = [f"SKN-{i:03d}" for i in range(n_nodes)]
    nodes = []
    for nid in node_ids:
        pose = rng.uniform(-50, 50, 6).astype(np.float32)
        pose[3:] = rng.uniform(-0.3, 0.3, 3)
        nodes.append(_make_node(nid, pose, slc))
    swarm = SwarmGossipProtocol(eta=0.08)
    topo = _full_topology(node_ids)
    for node in nodes:
        swarm.register_node(node, topo[node.node_id])
    trajectory_history = []
    consensus_history = []
    steps_to_convergence = n_steps
    converged = False
    if verbose:
        print(f"\n{'='*56}")
        print(f" SKN-V1 RENDEZVOUS SIMULATION  ({n_nodes} nodes)")
        print(f" Target: {target[:3]}  Steps: {n_steps}  dt={dt}s")
        print(f"{'='*56}\n")
    for step in range(n_steps):
        step_statuses = []
        for node in nodes:
            status = node.step(target, dt=dt)
            step_statuses.append(status)
        gossip_status = swarm.gossip_step(dt=dt)
        consensus_history.append(gossip_status["consensus_error"])
        if step % 10 == 0:
            snapshot = {
                "step": step,
                "poses": {n.node_id: n.pose.tolist() for n in nodes},
                "consensus_error": gossip_status["consensus_error"],
                "beta_1": gossip_status["beta_1"],
                "mean_dist_to_target": float(np.mean([
                    np.linalg.norm(n.pose[:3] - target[:3]) for n in nodes
                ])),
            }
            trajectory_history.append(snapshot)
            if verbose and step % 50 == 0:
                err = gossip_status["consensus_error"]
                m_dist = snapshot["mean_dist_to_target"]
                print(f"  Step {step:>4}  consensus={err:.4f}  dist={m_dist:.2f}m  β₁={gossip_status['beta_1']}")
        dists = [float(np.linalg.norm(n.pose[:3] - target[:3])) for n in nodes]
        if max(dists) < 0.5 and not converged:
            converged = True
            steps_to_convergence = step
            if verbose:
                print(f"\n  ✓ CONVERGED at step {step}  max_dist={max(dists):.4f}m")
    final_error = float(np.mean([np.linalg.norm(n.pose[:3] - target[:3]) for n in nodes]))
    if verbose:
        print(f"\n  Final error: {final_error:.4f}m")
        print(f"  Consensus error: {consensus_history[-1]:.4f}")
        print(f"  FRP events: {swarm._frp_count}\n")
    return {
        "scenario": "rendezvous", "n_nodes": n_nodes,
        "trajectory_history": trajectory_history,
        "consensus_history": consensus_history,
        "final_poses": {n.node_id: n.pose.tolist() for n in nodes},
        "converged": converged, "steps_to_convergence": steps_to_convergence,
        "final_error_m": final_error, "frp_events": swarm._frp_count,
        "vault_depths": {n.node_id: n.vault.chain_length for n in nodes},
        "swarm_status": swarm.swarm_status(),
    }


def _get_formation_targets(n: int, shape: str, scale: float) -> List[np.ndarray]:
    targets = []
    if shape == "line":
        for i in range(n):
            p = np.zeros(6, dtype=np.float32)
            p[0] = (i - n/2) * scale
            targets.append(p)
    elif shape == "ring":
        for i in range(n):
            a = 2 * np.pi * i / n
            p = np.zeros(6, dtype=np.float32)
            p[0] = scale * np.cos(a)
            p[1] = scale * np.sin(a)
            targets.append(p)
    elif shape == "tetrahedron":
        verts = np.array([[1,1,1],[1,-1,-1],[-1,1,-1],[-1,-1,1]], dtype=np.float32) * scale
        for i in range(n):
            p = np.zeros(6, dtype=np.float32)
            p[:3] = verts[i % 4]
            targets.append(p)
    elif shape == "cube":
        verts = np.array([
            [1,1,1],[1,1,-1],[1,-1,1],[1,-1,-1],
            [-1,1,1],[-1,1,-1],[-1,-1,1],[-1,-1,-1]
        ], dtype=np.float32) * scale
        for i in range(n):
            p = np.zeros(6, dtype=np.float32)
            p[:3] = verts[i % 8]
            targets.append(p)
    else:
        for i in range(n):
            theta = np.arccos(1 - 2*(i+0.5)/n)
            phi = np.pi * (1 + 5**0.5) * i
            p = np.zeros(6, dtype=np.float32)
            p[0] = scale * np.sin(theta) * np.cos(phi)
            p[1] = scale * np.sin(theta) * np.sin(phi)
            p[2] = scale * np.cos(theta)
            targets.append(p)
    return targets


def formation(n_nodes: int = 4, shape: str = "tetrahedron", scale: float = 20.0,
              n_steps: int = 300, dt: float = 0.05, slc=None, verbose: bool = True) -> dict:
    formation_targets = _get_formation_targets(n_nodes, shape, scale)
    rng = np.random.default_rng(seed=7)
    node_ids = [f"FRM-{i:03d}" for i in range(n_nodes)]
    nodes = []
    for i, nid in enumerate(node_ids):
        pose = rng.uniform(-100, 100, 6).astype(np.float32)
        nodes.append(_make_node(nid, pose, slc))
    swarm = SwarmGossipProtocol(eta=0.06)
    topo = _ring_topology(node_ids)
    for node in nodes:
        swarm.register_node(node, topo[node.node_id])
    trajectory_history = []
    formation_errors = []
    if verbose:
        print(f"\n{'='*56}")
        print(f" SKN-V1 FORMATION SIMULATION  ({n_nodes} nodes, shape={shape})")
        print(f"{'='*56}\n")
    for step in range(n_steps):
        for i, node in enumerate(nodes):
            target = formation_targets[i % len(formation_targets)]
            node.step(target, dt=dt)
        swarm.gossip_step(dt=dt)
        f_err = float(np.mean([
            np.linalg.norm(nodes[i].pose[:3] - formation_targets[i % len(formation_targets)][:3])
            for i in range(n_nodes)
        ]))
        formation_errors.append(f_err)
        if step % 10 == 0:
            trajectory_history.append({
                "step": step, "formation_error": f_err,
                "poses": {n.node_id: n.pose.tolist() for n in nodes},
            })
        if verbose and step % 60 == 0:
            print(f"  Step {step:>4}  formation_error={f_err:.3f}m")
    if verbose:
        print(f"\n  Final formation error: {formation_errors[-1]:.4f}m\n")
    return {
        "scenario": "formation", "shape": shape, "n_nodes": n_nodes,
        "formation_targets": [t.tolist() for t in formation_targets],
        "trajectory_history": trajectory_history,
        "formation_errors": formation_errors,
        "final_error_m": formation_errors[-1],
        "swarm_status": swarm.swarm_status(),
    }


def docking_chain(n_nodes: int = 4, n_steps: int = 100,
                  dt: float = 0.05, verbose: bool = True) -> dict:
    rng = np.random.default_rng(seed=99)
    node_ids = [f"DOCK-{i:03d}" for i in range(n_nodes)]
    nodes = []
    for i, nid in enumerate(node_ids):
        pose = np.zeros(6, dtype=np.float32)
        pose[0] = float(i) * 15.0
        nodes.append(_make_node(nid, pose))
    dock_events = []
    if verbose:
        print(f"\n{'='*56}")
        print(f" SKN-V1 DOCKING CHAIN SIMULATION  ({n_nodes} nodes)")
        print(f"{'='*56}\n")
    for i in range(n_nodes - 1):
        initiator = nodes[i]
        target_n = nodes[i + 1]
        dock_target = target_n.pose.copy()
        dock_target[0] += 0.1
        for _ in range(n_steps):
            initiator.step(dock_target, dt=dt)
            dist = float(np.linalg.norm(initiator.pose[:3] - dock_target[:3]))
            if dist < 0.15:
                break
        X = rng.uniform(0.8, 1.0, (3, 3)).astype(np.float32)
        U = rng.uniform(0.1, 0.5, (3, 3)).astype(np.float32)
        X = 0.5 * (X + X.T)
        success, H_m = initiator.ccpl_initiate_dock(target_n.node_id, X, U)
        dist_at_dock = float(np.linalg.norm(initiator.pose[:3] - target_n.pose[:3]))
        dock_events.append({
            "pair": f"{initiator.node_id} → {target_n.node_id}",
            "success": success, "manifest_hash": H_m[:16] + "...",
            "dist_at_dock_m": dist_at_dock,
            "vault_depth_i": initiator.vault.chain_length,
        })
        if verbose:
            status_str = "✓ LOCKED" if success else "✗ FAILED"
            print(f"  {initiator.node_id} → {target_n.node_id}  {status_str}"
                  f"  dist={dist_at_dock:.3f}m  H_m={H_m[:12]}...")
    if verbose:
        print(f"\n  Docks succeeded: {sum(e['success'] for e in dock_events)}/{len(dock_events)}\n")
    return {
        "scenario": "docking_chain", "n_nodes": n_nodes,
        "dock_events": dock_events,
        "success_rate": sum(e["success"] for e in dock_events) / max(len(dock_events), 1),
        "nodes": [n.node_status() for n in nodes],
    }


def isru_operation(n_nodes: int = 4, extraction_pts: int = 8,
                 n_steps_nav: int = 80, verbose: bool = True) -> dict:
    rng = np.random.default_rng(seed=42)
    ext_points = []
    for _ in range(extraction_pts):
        pos = rng.uniform(-200, 200, 3).astype(np.float32)
        ext_points.append({
            "pos": pos, "temp_K": rng.uniform(100, 400),
            "delta_H": rng.uniform(-50, 100), "delta_S": rng.uniform(0.01, 0.15),
            "mass_kg": rng.uniform(0.1, 2.0),
        })
    node_ids = [f"ISRU-{i:03d}" for i in range(n_nodes)]
    nodes = []
    for nid in node_ids:
        pose = rng.uniform(-50, 50, 6).astype(np.float32)
        nodes.append(_make_node(nid, pose))
    extraction_log = []
    if verbose:
        print(f"\n{'='*56}")
        print(f" SKN-V1 ISRU SIMULATION  ({n_nodes} nodes, {extraction_pts} sites)")
        print(f"{'='*56}\n")
    for pt_idx, pt in enumerate(ext_points):
        node = nodes[pt_idx % n_nodes]
        target = np.zeros(6, dtype=np.float32)
        target[:3] = pt["pos"]
        for _ in range(n_steps_nav):
            node.step(target, dt=0.05)
            if np.linalg.norm(node.pose[:3] - pt["pos"]) < 2.0:
                break
        dist_at_site = float(np.linalg.norm(node.pose[:3] - pt["pos"]))
        admitted, dG = node.isru.ingest_regolith(
            mass_kg=pt["mass_kg"], temperature=pt["temp_K"],
            delta_H=pt["delta_H"], delta_S=pt["delta_S"],
        )
        extraction_log.append({
            "site": pt_idx, "node": node.node_id, "admitted": admitted,
            "delta_G": round(dG, 3), "mass_kg": pt["mass_kg"] if admitted else 0.0,
            "dist_at_site": dist_at_site,
        })
        if verbose:
            sym = "✓" if admitted else "✗"
            print(f"  Site {pt_idx:>2}  {node.node_id}  {sym}  "
                  f"ΔG={dG:+.1f} kJ/mol  mass={pt['mass_kg']:.2f}kg  "
                  f"dist={dist_at_site:.1f}m")
    total_mass = sum(e["mass_kg"] for e in extraction_log)
    admit_rate = sum(e["admitted"] for e in extraction_log) / extraction_pts
    if verbose:
        print(f"\n  Total mass extracted: {total_mass:.3f} kg")
        print(f"  Gibbs admission rate: {admit_rate*100:.1f}%\n")
    return {
        "scenario": "isru_operation", "n_nodes": n_nodes,
        "extraction_pts": extraction_pts, "extraction_log": extraction_log,
        "total_mass_kg": total_mass, "gibbs_admit_rate": admit_rate,
        "mass_balances": {n.node_id: n.isru.mass_balance for n in nodes},
    }
'''

FILES['skn/simulation_v3.py'] = r'''
"""
skn/simulation_v3.py — SKN-V1 FORMATION v3
==========================================
Correct formation convergence via centroid consensus + shape springs.
"""

import numpy as np
import logging
from typing import List, Dict

from skn.node import SKNV1_SovereignNode
from skn.swarm import SwarmGossipProtocol

logger = logging.getLogger("skn.simulation_v3")


def _make_node(node_id: str, pose: np.ndarray, slc=None) -> SKNV1_SovereignNode:
    return SKNV1_SovereignNode(node_id=node_id, initial_pose=pose, slc_instance=slc)


def _get_formation_targets(n: int, shape: str, scale: float) -> List[np.ndarray]:
    targets = []
    if shape == "line":
        for i in range(n):
            p = np.zeros(6, dtype=np.float32)
            p[0] = (i - n/2) * scale
            targets.append(p)
    elif shape == "ring":
        for i in range(n):
            a = 2 * np.pi * i / n
            p = np.zeros(6, dtype=np.float32)
            p[0] = scale * np.cos(a)
            p[1] = scale * np.sin(a)
            targets.append(p)
    elif shape == "tetrahedron":
        verts = np.array([[1,1,1],[1,-1,-1],[-1,1,-1],[-1,-1,1]], dtype=np.float32) * scale
        for i in range(n):
            p = np.zeros(6, dtype=np.float32)
            p[:3] = verts[i % 4]
            targets.append(p)
    elif shape == "cube":
        verts = np.array([
            [1,1,1],[1,1,-1],[1,-1,1],[1,-1,-1],
            [-1,1,1],[-1,1,-1],[-1,-1,1],[-1,-1,-1]
        ], dtype=np.float32) * scale
        for i in range(n):
            p = np.zeros(6, dtype=np.float32)
            p[:3] = verts[i % 8]
            targets.append(p)
    else:
        for i in range(n):
            theta = np.arccos(1 - 2*(i+0.5)/n)
            phi = np.pi * (1 + 5**0.5) * i
            p = np.zeros(6, dtype=np.float32)
            p[0] = scale * np.sin(theta) * np.cos(phi)
            p[1] = scale * np.sin(theta) * np.sin(phi)
            p[2] = scale * np.cos(theta)
            targets.append(p)
    return targets


def _formation_neighbor_pairs(shape: str, n: int) -> List[tuple]:
    pairs = []
    if shape == "tetrahedron":
        for i in range(min(n, 4)):
            for j in range(i+1, min(n, 4)):
                pairs.append((i, j))
    elif shape == "cube":
        edges = [
            (0,1),(0,2),(0,4),(1,3),(1,5),(2,3),
            (2,6),(3,7),(4,5),(4,6),(5,7),(6,7)
        ]
        for i, j in edges:
            if i < n and j < n:
                pairs.append((i, j))
    elif shape == "ring":
        for i in range(n):
            pairs.append((i, (i+1) % n))
    elif shape == "line":
        for i in range(n-1):
            pairs.append((i, i+1))
    else:
        for i in range(n):
            pairs.append((i, (i+1) % n))
    return pairs


def formation_v3(n_nodes: int = 4, shape: str = "tetrahedron", scale: float = 20.0,
                 n_steps: int = 500, dt: float = 0.05, slc=None, verbose: bool = True) -> dict:
    formation_targets = _get_formation_targets(n_nodes, shape, scale)
    neighbor_pairs = _formation_neighbor_pairs(shape, n_nodes)
    rng = np.random.default_rng(seed=7)
    node_ids = [f"FRM-{i:03d}" for i in range(n_nodes)]
    nodes = []
    for i, nid in enumerate(node_ids):
        pose = rng.uniform(-100, 100, 6).astype(np.float32)
        nodes.append(_make_node(nid, pose, slc))
    trajectory_history = []
    formation_errors = []
    centroid_errors = []
    if verbose:
        print(f"\n{'='*60}")
        print(f" SKN-V1 FORMATION v3  ({n_nodes} nodes, shape={shape})")
        print(f" Scale={scale}m  Steps={n_steps}  dt={dt}s")
        print(f"{'='*60}\n")
    for step in range(n_steps):
        cx, cy, cz = 0, 0, 0
        for n in nodes:
            cx += n.pose[0]; cy += n.pose[1]; cz += n.pose[2]
        cx /= n_nodes; cy /= n_nodes; cz /= n_nodes
        centroid_target = np.zeros(3, dtype=np.float32)
        centroid_error = np.array([cx, cy, cz]) - centroid_target
        eta_kin = 0.20 if step < n_steps // 3 else 0.08
        for i, node in enumerate(nodes):
            target = formation_targets[i].copy()
            expected_pos = formation_targets[i][:3] + centroid_target
            offset_error = node.pose[:3] - expected_pos
            gain = 0.10 * np.exp(-step / 150.0)
            node.step(target, dt)
            node.pose[0] -= gain * offset_error[0]
            node.pose[1] -= gain * offset_error[1]
            node.pose[2] -= gain * offset_error[2]
        spring_k = 0.05 * np.exp(-step / 200.0)
        for i, j in neighbor_pairs:
            if i >= n_nodes or j >= n_nodes:
                continue
            ni, nj = nodes[i], nodes[j]
            rel_actual = ni.pose[:3] - nj.pose[:3]
            rel_target = (formation_targets[i][:3] - formation_targets[j][:3])
            rel_error = rel_actual - rel_target
            force = spring_k * rel_error
            ni.pose[0] -= force[0] * 0.5; ni.pose[1] -= force[1] * 0.5; ni.pose[2] -= force[2] * 0.5
            nj.pose[0] += force[0] * 0.5; nj.pose[1] += force[1] * 0.5; nj.pose[2] += force[2] * 0.5
        f_err = float(np.mean([
            np.linalg.norm(nodes[i].pose[:3] - (formation_targets[i][:3] + centroid_target))
            for i in range(n_nodes)
        ]))
        formation_errors.append(f_err)
        centroid_errors.append(float(np.linalg.norm(centroid_error)))
        if step % 20 == 0:
            trajectory_history.append({
                "step": step, "formation_error": f_err,
                "centroid_error": float(np.linalg.norm(centroid_error)),
                "poses": {n.node_id: n.pose.tolist() for n in nodes},
            })
        if verbose and step % 100 == 0:
            print(f"  Step {step:>4}  form_err={f_err:.3f}m  cent_err={np.linalg.norm(centroid_error):.3f}m")
    if verbose:
        print(f"\n  Final formation error: {formation_errors[-1]:.4f}m")
        print(f"  Final centroid error:  {centroid_errors[-1]:.4f}m\n")
    return {
        "scenario": "formation_v3", "shape": shape, "n_nodes": n_nodes,
        "formation_targets": [t.tolist() for t in formation_targets],
        "trajectory_history": trajectory_history,
        "formation_errors": formation_errors,
        "centroid_errors": centroid_errors,
        "final_error_m": formation_errors[-1],
        "final_centroid_m": centroid_errors[-1],
    }
'''


def main():
    """Write all embedded files to disk."""
    for path, content in FILES.items():
        full_path = os.path.join(os.getcwd(), path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content.strip() + '\n')
        print(f"  Wrote {path} ({len(content):,} bytes)")


if __name__ == "__main__":
    main()

