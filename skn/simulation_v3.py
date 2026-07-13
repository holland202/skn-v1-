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
