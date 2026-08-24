# SKN-V1 — Target Design

STATUS: none of this is built. This document is the design SKN-V1 is aimed
at, moved out of README.md on 2026-08-10 because it was written in present
tense there and read as a description of working software. It is kept intact,
unedited, as a roadmap.

What actually runs today is in README.md: five subsystems, 15 tests, one demo
script, simulation only, no hardware. The four subsystems below -- hardware
abstraction, the SE(2) projection, post-quantum C-CPL, and the ROS2 bridge --
are designed and not implemented.

The BOM, timings and version numbers in this file are design targets. No part
of it has been measured on hardware, because no hardware exists.

---

## Hardware Demo

### BOM (Bill of Materials) — $100/node

| Component | Model | Cost | Purpose |
|-----------|-------|------|---------|
| Compute | Raspberry Pi 4 (4 GB) | $55 | Main controller, ROS2 node |
| MCU | STM32F407VGT6 | $12 | Real-time PWM, encoder reading |
| IMU | MPU-9250 | $8 | 9-DOF pose estimation |
| Radio | nRF24L01+ | $3 | 2.4 GHz inter-node mesh |
| Motor driver | DRV8833 | $4 | Dual H-bridge, 1.2 A/channel |
| Chassis | 3D-printed | $8 | Custom frame, ~200 g |
| Battery | 2S LiPo 1000 mAh | $10 | ~30 min runtime |

### SE(3) → SE(2) Projection

For ground robots, the full SE(3) pose is projected to SE(2) by fixing z = 0 and pitch = roll = 0:

```python
# In skn/hardware_abstraction.py
def project_se3_to_se2(g_se3: np.ndarray) -> np.ndarray:
    """Project homogeneous SE(3) matrix to SE(2).

    g_se3: 4x4 homogeneous matrix [R | t; 0 | 1]
    Returns: 3x3 SE(2) matrix [cos θ, -sin θ, x; sin θ, cos θ, y; 0, 0, 1]
    """
    x, y = g_se3[0, 3], g_se3[1, 3]
    theta = np.arctan2(g_se3[1, 0], g_se3[0, 0])
    return np.array([
        [np.cos(theta), -np.sin(theta), x],
        [np.sin(theta),  np.cos(theta), y],
        [0, 0, 1]
    ])
```

This projection is **lossless for planar motion** and allows the same control stack to run on aerial (full SE(3)) and ground (SE(2)) platforms without modification.

### Calibration

```bash
# IMU calibration (run once per node)
python scripts/calibrate_imu.py --duration 60 --output imu_cal.json

# Motor PID tuning
python scripts/tune_pid.py --kp 1.2 --ki 0.05 --kd 0.3 --target_vel 0.5

# Radio mesh test
python scripts/test_mesh.py --channel 76 --power 0dBm --nodes 4
```

---

## Crypto Hardening

### Current State (v1.7.1)

**Correction, kept (2026-08-23).** This table previously marked manifest
signing and the hash chain "Implemented" with per-operation Snapdragon
timings. That contradicted this file's own header, which states that none of
this is built and that no part of it has been measured on hardware. The
timings were never measured. Withdrawn: "ML-DSA-65, Implemented, 5.1 ms/sign"
and "SHA3-512, Implemented, 0.1 ms/hash".

| Primitive | Standard | Status | Performance |
|-----------|----------|--------|-------------|
| Manifest signing | ML-DSA-65 (FIPS 204) | 🔴 Not built | NOT MEASURED. The code computes an unauthenticated SHA-256 digest of two public values instead; see README section 3 |
| Hash chain | SHA3-512 (FIPS 202) | 🟢 Built, unbenchmarked | NOT MEASURED. The chain exists in `skn/node.py` and its verify path recomputes each link; no timing run exists |
| Key exchange | Kyber-768 placeholder | 🟡 Stub | N/A |
| Zero-knowledge proof | Placeholder | 🔴 Not started | N/A |

### Migration Path

| Version | Milestone | ETA |
|---------|-----------|-----|
| v1.8.0 | Replace Kyber placeholder with ML-KEM-768 | Q3 2026 |
| v1.9.0 | Add zk-SNARK for private consensus verification | Q4 2026 |
| v2.0.0 | Full PQ hardening audit + NIST compliance docs | Q1 2027 |

---

## ROS2 Bridge

### Topics

| Topic | Type | QoS | Publisher | Description |
|-------|------|-----|-----------|-------------|
| `/swarm/pose_array` | `geometry_msgs/PoseArray` | reliable, depth 10 | SKN node | All node poses |
| `/skn/health` | `diagnostic_msgs/DiagnosticArray` | best effort | SKN node | β₁, battery, signal |
| `/skn/vault/head` | `std_msgs/String` | reliable, depth 1 | Evidence Vault | Current Merkle root |

### Services

| Service | Type | Description |
|---------|------|-------------|
| `/skn/dock_request` | `skn_v1/DockRequest` | Initiate C-CPL handshake with target node |
| `/skn/topo/query` | `skn_v1/TopologyQuery` | Request current β₁ barcode |
| `/skn/param/set` | `skn_v1/SetParam` | Runtime parameter update (η, gossip rate, etc.) |

### Launch

```bash
# Single node (development)
ros2 run skn_v1 skn_ros2_node --ros-args -p node_id:=0 -p n_nodes:=4

# Full swarm (4 nodes, simulation)
ros2 launch skn_v1 swarm_demo.launch.py n_nodes:=4 formation:=tetrahedron

# Hardware swarm (8 nodes, RPi 4)
ros2 launch skn_v1 swarm_hw.launch.py n_nodes:=8 target:=hw_bom_v1
```

---
