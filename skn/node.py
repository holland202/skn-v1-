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
        self._records: List[dict] = []   # preimages for real re-verification
        self._prev_hash: bytes = b'\x00' * 64
        self._vault_path = vault_path

    def commit(self, state_vector: np.ndarray, metadata: dict = None) -> bytes:
        # Store the exact preimage bytes so the chain can be RE-VERIFIED later
        # (fix 2026-07-20: the old vault kept only hashes, so verify_chain had
        # nothing to recompute against and was vacuous).
        s_bytes = (
            state_vector.astype(np.float32).tobytes() +
            str(metadata or {}).encode() +
            str(time.time_ns()).encode()
        )
        h = hashlib.sha3_512(s_bytes + self._prev_hash).digest()
        self._records.append({"preimage": s_bytes, "prev": self._prev_hash, "hash": h})
        self._chain.append(h)
        self._prev_hash = h
        if len(self._chain) > 256:
            self._chain = self._chain[-256:]
            self._records = self._records[-256:]
        return h

    def verify_chain(self) -> bool:
        # REAL tamper-evidence (fix 2026-07-20): recompute every link and confirm
        # (a) each hash matches sha3_512(preimage + prev) and (b) each link's prev
        # equals the previous link's hash. Any edit to any state, metadata, hash,
        # or ordering breaks the chain and returns False. The old version returned
        # `len(self._chain) >= 0`, which is ALWAYS true and verified nothing.
        expected_prev = b"\x00" * 64
        for rec in self._records:
            if rec["prev"] != expected_prev:
                return False
            if hashlib.sha3_512(rec["preimage"] + rec["prev"]).digest() != rec["hash"]:
                return False
            expected_prev = rec["hash"]
        return True

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
