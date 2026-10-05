"""
skn/node.py — SKN-V1 SOVEREIGN KINEMATIC NODE
===============================================
Full software implementation of the Sovereign Kinematic Node.
"""

import numpy as np
import hashlib
import json
import os
import time
import logging
from typing import Optional, Dict, Tuple, List

logger = logging.getLogger("skn.node")


class PropulsionAllocator:
    """Map SE(3) velocity commands to HET + CMG actuator commands."""

    GEOMETRIES = ("legacy", "paired")

    def __init__(self, num_hets: int = 6, cmg_saturation: float = 0.95, geometry: str = "legacy",
                 clip: bool = True):
        """geometry "legacy": num_hets HETs, every one tilted +0.3 in z, so no command can push -z.
        geometry "paired" (K3, 2026-10-05): the same azimuths twice, tilted +0.3 and -0.3 in z
        (2 * num_hets HETs), so -z is realizable. clip=False disables HET/CMG limits (test use only)."""
        if geometry not in self.GEOMETRIES:
            raise ValueError(f"geometry must be one of {self.GEOMETRIES}")
        self.geometry = geometry
        self.clip = clip
        self.num_hets = num_hets * (2 if geometry == "paired" else 1)
        self.cmg_saturation = cmg_saturation
        self.max_thrust = 0.025
        self.isp = 2000.0
        self.B = self._build_allocation_matrix(num_hets)
        self.B_inv = np.linalg.pinv(self.B)

    def _build_allocation_matrix(self, n_hets: int) -> np.ndarray:
        tilts = (0.3, -0.3) if self.geometry == "paired" else (0.3,)
        B = np.zeros((6, n_hets * len(tilts) + 3))
        angles = np.linspace(0, 2 * np.pi, n_hets, endpoint=False)
        col = 0
        for tz in tilts:
            for a in angles:
                B[0:3, col] = [np.cos(a), np.sin(a), tz]
                col += 1
        B[3:6, -3:] = np.eye(3)
        return B

    def allocate(self, cmd_6dof: np.ndarray, current_mass: float = 1.0) -> np.ndarray:
        u = self.B_inv @ cmd_6dof.astype(np.float64)
        mass_scale = 1.0 / np.cbrt(max(current_mass, 0.1))
        u *= mass_scale
        n_het = self.num_hets
        if self.clip:
            u[:n_het] = np.clip(u[:n_het], 0.0, 1.0)
            u[-3:] = np.clip(u[-3:], -self.cmg_saturation, self.cmg_saturation)
        return u.astype(np.float32)

    def realize(self, u: np.ndarray, current_mass: float = 1.0) -> np.ndarray:
        """The 6-DOF command the actuators actually produce: B u, with allocate()'s mass scaling undone,
        so an unclipped u reproduces the command exactly (K3)."""
        mass_scale = 1.0 / np.cbrt(max(current_mass, 0.1))
        return (self.B @ u.astype(np.float64) / mass_scale).astype(np.float32)

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
        # prev of the oldest RETAINED record. Starts at genesis; moves when old records are dropped
        # (K4, 2026-10-05). Dropped records cannot be re-verified by anyone.
        self._anchor: bytes = b'\x00' * 64
        self._vault_path = vault_path
        # K6 (2026-10-05): with a path, every record is appended to a JSONL file, so records dropped from the
        # 256-record window stay checkable. An existing file is verified first and the chain continues from
        # it; a file that does not verify is refused (fail closed). The file is not signed (see README).
        if vault_path is not None and os.path.exists(vault_path) and os.path.getsize(vault_path) > 0:
            ok, last = self._walk_file(vault_path, check_hashes=True)
            if not ok:
                raise ValueError(f"evidence vault file {vault_path} does not verify; refusing to extend it")
            self._prev_hash = self._anchor = last

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
        if self._vault_path is not None:
            with open(self._vault_path, "a") as fh:
                fh.write(json.dumps({"preimage": s_bytes.hex(), "prev": self._records[-1]["prev"].hex(),
                                     "hash": h.hex()}) + "\n")
                fh.flush()
        if len(self._chain) > 256:
            self._chain = self._chain[-256:]
            self._records = self._records[-256:]
            self._anchor = self._records[0]["prev"]
        return h

    def verify_chain(self) -> bool:
        # REAL tamper-evidence (fix 2026-07-20): recompute every link and confirm
        # (a) each hash matches sha3_512(preimage + prev) and (b) each link's prev
        # equals the previous link's hash. Any edit to any state, metadata, hash,
        # or ordering breaks the chain and returns False. The old version returned
        # `len(self._chain) >= 0`, which is ALWAYS true and verified nothing.
        # Start from the anchor, not genesis: before K4 (2026-10-05) an untampered vault with more than
        # 256 commits failed here, because the retained window no longer starts at genesis.
        expected_prev = self._anchor
        for rec in self._records:
            if rec["prev"] != expected_prev:
                return False
            if hashlib.sha3_512(rec["preimage"] + rec["prev"]).digest() != rec["hash"]:
                return False
            expected_prev = rec["hash"]
        return True

    @staticmethod
    def _walk_file(path: str, check_hashes: bool = True) -> Tuple[bool, bytes]:
        expected_prev = b'\x00' * 64
        try:
            with open(path) as fh:
                for line in fh:
                    rec = json.loads(line)
                    pre, prev, h = (bytes.fromhex(rec[k]) for k in ("preimage", "prev", "hash"))
                    if prev != expected_prev:
                        return False, expected_prev
                    if check_hashes and hashlib.sha3_512(pre + prev).digest() != h:
                        return False, expected_prev
                    expected_prev = h
        except (OSError, ValueError, KeyError, TypeError):
            return False, expected_prev
        return True, expected_prev

    @staticmethod
    def verify_file(path: str) -> bool:
        """Walk a vault file from the all-zero genesis, recomputing every hash (K6). Detects edits, deletions
        and reordering anywhere in the file. Does NOT detect removal of the newest lines (tail truncation), and
        cannot detect a consistent rewrite of the whole file: the chain is unkeyed."""
        return EvidenceVault._walk_file(path, check_hashes=True)[0]

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
                 slc_instance=None, vault_path: Optional[str] = None,
                 closed_loop: bool = False, thruster_geometry: str = "legacy"):
        """closed_loop=True (K3, 2026-10-05): the pose moves by what the thrusters realize, not by the command.
        Defaults (open loop, legacy thrusters) are unchanged; which SKN should use is an open design decision."""
        self.node_id = node_id
        self.closed_loop = closed_loop
        self.pose = (initial_pose.astype(np.float32).copy()
                     if initial_pose is not None
                     else np.zeros(6, dtype=np.float32))
        self.velocity = np.zeros(6, dtype=np.float32)
        self.fisher_metric = np.eye(6, dtype=np.float32)
        self.current_mass = 1.0
        self.inertia_tensor = np.eye(3, dtype=np.float32)
        self.c_cpl_locked = False
        self.propulsion = PropulsionAllocator(geometry=thruster_geometry)
        self.vault = EvidenceVault(vault_path)
        self.isru = ISRUMonitor()
        self.slc = slc_instance
        self._step_count = 0
        self._dock_count = 0
        self._dock_keys = None  # (public, secret) ML-DSA-65 keys, made at the first dock
        self.last_dock_record = None
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
        actuator_cmds = self.propulsion.allocate(grad, self.current_mass)
        move = self.propulsion.realize(actuator_cmds, self.current_mass) if self.closed_loop else grad
        self.velocity = move
        self.pose += move * dt
        self._step_count += 1
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
        """Dock only with an ML-DSA-65 signature on the manifest (skn.ccpl, K2). Returns (locked, detail):
        detail is the manifest's SHA3-512 on success, or why nothing locked. Fails closed without dilithium-py.
        Before 2026-09-27 the "signature" was SHA256(SHA3-256(manifest) || node_id), two public values."""
        from . import ccpl
        if not ccpl.available():
            return False, ccpl.UNAVAILABLE
        if self._dock_keys is None:
            self._dock_keys = ccpl.keygen()
        pk, sk = self._dock_keys
        align_quality = float(np.trace(alignment_tensor))
        if align_quality <= 0.5:
            return False, f"alignment quality {align_quality:.3f} <= 0.5"
        manifest = ccpl.make_manifest(self.node_id, target_node_id, self.pose,
                                      np.asarray(alignment_tensor).ravel(), np.asarray(strain_energy).ravel())
        record = ccpl.sign_manifest(manifest, pk, sk)
        self.last_dock_record = record
        self.c_cpl_locked = True
        self._dock_count += 1
        self.vault.commit(self.pose, {
            "event": "CCPL_DOCK", "target": target_node_id, "dock_n": self._dock_count,
            "manifest_sha3_512": record["manifest_sha3_512"][:32],
            "signature_sha3_256": hashlib.sha3_256(bytes.fromhex(record["signature"])).hexdigest()[:32],
            "public_key_sha3_256": record["public_key_sha3_256"][:32],
        })
        return True, record["manifest_sha3_512"]

    @property
    def dock_public_key(self) -> Optional[bytes]:
        return None if self._dock_keys is None else self._dock_keys[0]

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
