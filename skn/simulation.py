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
