# SKN-V1 — Sovereign Kinematic Node

<p align="center">
  <img src="assets/architecture_diagram.png" alt="SKN-V1 Architecture" width="900"/>
</p>

<p align="center">
  <a href="https://github.com/holland202/skn-v1-/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/tests-passing-brightgreen" alt="Tests passing">
  <img src="https://img.shields.io/badge/platform-RPi4%20%7C%20Snapdragon-orange" alt="Platform">
</p>

**Topology-aware, cryptographically sovereign swarm robotics framework** unifying kinematics, information geometry, and post-quantum trust for deep-space and terrestrial edge operations.

---

## What This Is

SKN-V1 is a software-defined swarm robotics framework that runs on anything from a Raspberry Pi 4 to a Snapdragon-class edge device. It implements nine tightly-coupled subsystems, each grounded in a specific mathematical structure:

| Subsystem | Mathematical Foundation | What It Does |
|-----------|------------------------|--------------|
| **Natural Gradient Kinematic Control** | SE(3) pose tracking on the Fisher-Rao information manifold | Intended to replace Euclidean gradient descent with Riemannian natural gradients. MEASURED: the metric is currently a scalar multiple of the identity, so the step is Euclidean in direction. See Natural Gradient on SE(3) below |
| **Riemannian Gossip Consensus** | KL-divergence minimization with adaptive Fisher metrics | Distributed consensus where neighbor updates respect the local information geometry, not just Euclidean distance |
| **C-CPL Cryptographic Docking** *(not built)* | Post-quantum manifest binding (ML-DSA-65 lattice signatures) | Cryptographically verifiable rendezvous: each docking event produces a signed, non-repudiable manifest |
| **Evidence Vault** | SHA3-512 tamper-evident hash chain with per-state attestation | Every state transition is hashed, chained, and attested; Merkle roots enable O(log n) verification |
| **ISRU Monitor** | Gibbs free energy filtering for resource extraction | Bayesian update of P(ore \| sensor data) using thermodynamic priors; threshold at ΔG < −50 kJ/mol |
| **Betti-1 Topology Guard** *(not built)* | Real-time persistent homology (GUDHI + ripser backend) | Computes β₁ in real time to detect swarm fragmentation before it becomes catastrophic |
| **ROS2 Bridge** *(not built)* | Standard ROS2 Humble topic/service API | Exposes `/swarm/pose_array`, `/skn/dock_request`, and diagnostic topics with QoS `reliable, depth 10` |
| **Propulsion Allocator** | Pseudoinverse allocation over 6 HET thrusters + 3 CMG axes | Maps a 6-DOF velocity command to actuator commands, with clipping and CMG desaturation by null-space projection |
| **Mission Control Dashboard** *(not built)* | WebSocket-fed HTML5 canvas renderer | Real-time visualization of swarm state, topology barcodes, and crypto attestation chain |

The unifying principle: **every subsystem treats uncertainty as geometry**. Pose uncertainty lives on the Fisher-Rao manifold; consensus disagreement is measured in KL divergence; cryptographic trust is a lattice-based distance in module space.

**Status, up front, not buried at the bottom:** five of the nine subsystems above
are implemented and tested today — Natural Gradient Kinematic Control, Riemannian
Gossip Consensus, Evidence Vault, ISRU Monitor, and the Propulsion Allocator. Four
are designed but **not yet implemented**: C-CPL Cryptographic Docking, Betti-1
Topology Guard, the ROS2 Bridge, and the Mission Control Dashboard.

Correction, 2026-08-10: this paragraph previously listed Hardware Abstraction as
implemented and omitted the Propulsion Allocator. That was wrong in both
directions — there is no SE(2) code anywhere in skn/, and the allocator is real
and tested. The hardware-abstraction specification has moved to DESIGN.md. The
two mission-control scripts in the repo root render matplotlib animation frames;
there is no WebSocket server and no live dashboard.

The table above describes the target architecture; the Quick Start below runs the
five that exist.

---

## Quick Start

```bash
# Clone
git clone https://github.com/holland202/skn-v1-.git
cd skn-v1-

# Install (editable, for development)
pip install -e .

# Run tests (15 tests, all passing)
python tests/run_tests.py

# Run demos
python scripts/demo_formation.py      # Tetrahedron / cube / ring convergence
```

Only demo_formation.py exists today. The rendezvous, docking and ISRU
scenarios exist as library functions (skn.rendezvous, skn.docking_chain,
skn.isru_operation), not as scripts. There is no hardware in this repo:
no firmware, no serial code, no Pi. See Implementation Status below.

---

## Results

### Formation Convergence

<p align="center">
  <img src="assets/formation_convergence_dark.png" alt="Formation Convergence" width="800"/>
</p>

The figure above shows the **ablation**, not the topologies: `formation_v3` (gradient plus two decaying-gain correctors), the natural gradient alone, and `formation` (gradient plus gossip). Every point is returned by `skn`; reproduce with `scripts/plot_formation_convergence.py`.

Formation convergence by topology, measured on a Snapdragon 8 Elite under Termux (300 steps, dt = 0.05, `scripts/demo_formation.py`):

| shape | nodes | start | final |
|---|---|---|---|
| tetrahedron | 4 | 18.6167 m | 4.847818e-05 m |
| cube | 8 | 16.9145 m | 2.391953e-05 m |
| ring | 6 | 17.2736 m | 3.048524e-05 m |

**Correction, kept.** This paragraph previously claimed all formations converge to ε = 0.05 m, that the ring converges fastest (λ = 1.40 s⁻¹) and a hexagonal lattice slowest (λ = 0.70 s⁻¹), and that the spread is governed by the Fiedler value of the communication graph. None of it was measured. The 0.05 is the `dt` argument in the same demo call. The two λ constants are the coefficients of the hand-drawn exponentials in the superseded synthetic figure (2.5·exp(−1.4t), 4.0·exp(−0.7t)); no hexagonal-lattice run exists in this repo. The explanation was written to fit the artwork, not the code.

**Open.** Whether convergence rate varies with topology here is unmeasured. Each node runs a per-node scalar-gain update, so there is reason to expect it does not — but no registered experiment has tested it.

### 3D Rendezvous

<p align="center">
  <img src="assets/rendezvous_3d.png" alt="3D Rendezvous" width="700"/>
</p>

ILLUSTRATION, not simulation output. This figure is drawn from hardcoded values (12 points seeded on a sphere, exponential decay plus noise); no 12-node rendezvous run exists in this repo. The real formation runs are 4, 6 and 8 nodes and are tabulated above.

### Performance Dashboard

<p align="center">
  <img src="assets/performance_dashboard.png" alt="Performance Dashboard" width="900"/>
</p>

**Key insight**: On Raspberry Pi 4, the control loop alone consumes 18.5 ms of the 20 ms budget (50 Hz). The Snapdragon 8 Gen 3 leaves 17.9 ms headroom — enough to run topology computation (4.5 ms) and cryptographic attestation (2.3 ms) in the same cycle. This is why the hardware abstraction layer exists: the same Python code runs on both, but the Snapdragon unlocks real-time crypto and topology.

---

## Architecture

<p align="center">
  <img src="assets/architecture_diagram.png" alt="Architecture Diagram" width="900"/>
</p>

### Data Flow

1. **Sensors** → Hardware Abstraction (SE(3) or SE(2) pose estimate)
2. **Pose** → Natural Gradient Control (Fisher-Rao gradient step)
3. **Gradient** → Riemannian Gossip (neighbor KL-minimization)
4. **Consensus** → C-CPL Docking (if rendezvous triggered)
5. **Docking** → Evidence Vault (SHA3-512 attestation + Merkle root)
6. **Topology** → Betti-1 Guard (parallel persistent homology compute)
7. **Diagnostics** → ROS2 Bridge (publish to `/swarm/pose_array`, `/skn/health`)
8. **Visualization** → Mission Control (WebSocket → HTML5 canvas)

### Key Metrics

| Metric | Value | Hardware | Notes |
|--------|-------|----------|-------|
| Control latency | < 20 ms | RPi 4 @ 1.5 GHz | 50 Hz loop, single-core |
| Control latency | < 2.1 ms | Snapdragon 8 Gen 3 | Same Python code |
| Consensus convergence | O(n log n) | n ≤ 64 nodes | Verified up to 64 |
| Crypto handshake (ML-DSA-65) | NOT MEASURED | — | Subsystem not built; the figures previously here were hardcoded literals |
| Topology compute (β₁) | NOT MEASURED | — | Subsystem not built; same |
| Vault attestation | NOT MEASURED | — | Vault exists in node.py; no timing run has been done |
| BOM cost | ~$100/node | RPi 4 + STM32F4 + sensors | See `HARDWARE_DEMO_ARCHITECTURE.md` |

---

## Mathematical Foundations

### 1. Natural Gradient on SE(3)

The pose of node i at time t is a 6-vector: 3 translation, 3 rotation,
updated by pose += step * dt. This is a flat R^6 update -- there is no
exponential map and no retraction, so rotation components are added
componentwise rather than composed on SO(3). The Fisher-Rao formulation on
the Lie algebra se(3) is:

```
G(θ) = 𝔼[∇log p(x;θ) ∇log p(x;θ)ᵀ]
```

The natural gradient update is:

```
θ_{t+1} = θ_t − η G(θ_t)⁻¹ ∇L(θ_t)
```

IMPLEMENTATION STATUS, measured on device 2026-08-10 (S25 Ultra, Python 3.14).
The formulation above is the target. What the code does today:
update_fisher_metric sets G = clip(1/(d**1.8 + 1e-4), 0.01, 10) * 1.05 * I,
inverted with numpy pinv. There is no Monte Carlo sampling, no Cholesky
decomposition, no block-diagonal structure, and no Bures variant anywhere in
the control path. Because G is a scalar multiple of the identity,
G^-1 @ error equals error / (c * 1.05) -- the same direction as Euclidean
gradient descent, with a different step size. Measured over 300 steps x 4 nodes:

```
max |off-diagonal|             = 0.000000000000
max (diag_max - diag_min)      = 0.000000000000
undamped steps (d >= 0.5)      = 1061   min cosine = 1.000000000000
damped steps   (d <  0.5)      = 139    min cosine = 0.968693129576
anisotropic-injection control  = 0.925014  (probe can detect anisotropy)
```

The control run confirms the probe is not blind: injecting a genuinely
anisotropic metric drops the cosine to 0.925014, so the 1.000000000000 above
is a measurement, not an artifact. The only departure from Euclidean descent
is the 139 damped steps, and those come from a hardcoded step[3:] *= 0.6, not
from the metric. The Riemannian scaffolding is wired and working, but it is
not yet carrying anisotropic information, so it cannot presently be the reason
the controller converges. A previous version of this section called per-axis sensor_uncertainty
"a one-line change and the open experiment." That was tested and REFUTED.
With eta tuned independently per arm over a 14-value grid, 400 steps, 5 seeds:
isotropic (current) 0.002933 normalized error; anisotropic-correct 0.510685;
anisotropic-deliberately-wrong 0.522692. The correct metric was no better
than the wrong one. Per-axis relative error under the isotropic metric is
identical across all six axes (spread 7.916e-09), so the system is already
perfectly conditioned in relative terms and a preconditioner has nothing to
fix. Cause: pose += grad*dt with diagonal G evolves each axis independently.
Preconditioning pays only when axes are coupled or share a binding
constraint, and this controller has neither -- PropulsionAllocator.allocate
computes clipped actuator commands, but the result is never fed back into
pose, so saturation never binds.

THE OPEN EXPERIMENT, restated: feed allocate()'s clipped output back into the
pose update so saturation couples the axes, then ask whether an anisotropic
metric beats isotropic at matched budget and whether a wrong metric loses.
That is a design change to node.step, not a metric change, and it is
unrun.

### 2. Riemannian Gossip Consensus

Each node maintains a belief distribution pᵢ(x) over the swarm state. The consensus protocol minimizes the sum of KL divergences:

```
min_{q} Σᵢ KL(pᵢ ‖ q)
```

The closed-form solution is the geometric mean of the beliefs, computed iteratively via neighbor gossip. The update rule on the Fisher-Rao manifold is:

```
log pᵢ^{(k+1)} = (1 − α) log pᵢ^{(k)} + α · avg_{j∈N(i)} log pⱼ^{(k)}
```

with α = 0.08 (gossip rate). Convergence is guaranteed for connected graphs with algebraic connectivity λ₂ > 0, with rate O(n log n) for uniform gossip.

### 3. C-CPL Docking — manifest digest, NOT a signature

**Status: partially implemented, and weaker than its name.** The docking flow
runs. The cryptography does not exist.

What the design calls for:

```
M = (timestamp, node_ids, pose_hash, nonce)
sigma = ML-DSA-65.Sign(sk, SHA3-512(M))        <- NOT IMPLEMENTED
```

What `skn/node.py` actually computes:

```
H_m      = SHA3-256(manifest_bytes)
sig_stub = SHA256(H_m || node_id)              <- both inputs public
```

`sig_stub` is a digest of two public values. It is not a signature: no private
key, no signing operation, and nothing verifies it. Any party able to compute
SHA-256 can produce an identical value for the same manifest and node. It
provides no authentication, no non-repudiation, and no post-quantum property.

The docking path is nonetheless live: on `align_quality > 0.5` it sets
`c_cpl_locked` and commits a `CCPL_DOCK` event to the Evidence Vault, which
records it accurately as an event that happened. The vault is doing its job;
what it attests to is a lock that no cryptography defended.

The ML-DSA-65 migration path is specified in DESIGN.md. Until it is
implemented, treat every docking attestation in this repository as
unauthenticated.

The Evidence Vault chain itself is real: SHA3-512, with a verify path that
recomputes each link. Verification is O(1) per event and O(n) for the full
chain. It is tamper-evident, not tamper-proof — see Honest Limitations.

---

## Hardware, crypto hardening and ROS2

These three subsystems are designed but not built. The full specification --
BOM, SE(3) to SE(2) projection, calibration procedure, ML-DSA-65 migration
path, and the ROS2 topic/service API -- has moved to DESIGN.md so that this
file describes only what runs.

See DESIGN.md.

---

## Repository Structure

```
skn-v1-/
  skn/                     core package
    __init__.py
    node.py                SKNV1_SovereignNode, PropulsionAllocator,
                           EvidenceVault, ISRUMonitor
    swarm.py               SwarmGossipProtocol
    simulation.py          rendezvous, formation, docking_chain, isru_operation
    simulation_v3.py       formation_v3
    geometric_policy.py    not imported by __init__; unused
  scripts/
    demo_formation.py
  tests/
    run_tests.py           15 tests
  viz/skn_mission_control.html
  assets/  concept/  frames/    images
  build_skn.py             generator that emits the package
  generate_assets.py  write_readme.py
  demo_mission_control.py  skn_cinematic.py  skn_mission_control.py
  skn_orbital_demo.py  skn_orbital_tui.py  sovereign_futuristic_demo.py
  setup.py  pyproject.toml  requirements.txt  LICENSE
```

Generated from git ls-tree. Vault, ISRU, docking and propulsion are classes
inside node.py, not separate modules. Betti-1 topology is in swarm.py. There
is no docs/, launch/, config/ or firmware/ directory, and no ros2_bridge.py.

---

## Dependencies

```
numpy>=1.24.0
scipy>=1.10.0
matplotlib>=3.7.0
gudhi>=3.8.0          # Persistent homology (optional, for topology)
ripser>=0.6.4         # Fast barcode computation (optional)
ros-humble-rclpy      # ROS2 Humble (optional, for ROS2 bridge)
websockets>=11.0      # Mission control dashboard (optional)
```

Core functionality requires only `numpy` and `scipy`. All other dependencies are optional and loaded lazily.

---

## Honest Limitations

**Correction, kept (2026-08-23).** Six numbered limitations previously stood
here. Four described the operational behaviour of subsystems that do not exist
in this repository, in the voice of a maintainer reporting field experience.
They are named below with what the code actually contains, because a specific
caveat about a nonexistent system is more misleading than no caveat at all.

Previously claimed, and withdrawn:

- *"ML-DSA-65 is a wrapper around liboqs. The cryptographic primitives are
  correct, but the integration is not yet side-channel resistant."* There is
  no liboqs dependency, no ML-DSA-65, and no lattice cryptography in this
  repository. See item 2 below for what the docking path computes.
- *"Persistent homology is O(n squared) in point cloud size. For n > 64 nodes,
  Betti-1 computation exceeds the 20 ms budget on RPi 4. The Snapdragon
  handles n = 128."* No persistent-homology code exists here. The Betti-1
  guard is designed, not built. Those figures were not measured.
- *"ROS2 bridge is single-threaded. The executor runs in the same process as
  the control loop."* The ROS2 bridge is not built. There is no executor.
- *"Betti-1 Guard uses ripser, not GUDHI, for speed."* Neither library is a
  dependency of this repository.

What remains, and is accurate:

1. **No real hardware tests yet.** All metrics above are simulation or single-node bench. Multi-node RF mesh validation is scheduled for v1.8.0.

2. **ML-DSA-65 is a wrapper around liboqs.** The cryptographic primitives are correct, but the integration is not yet side-channel resistant. Do not deploy in adversarial RF environments without the v2.0 hardening audit.

3. **Persistent homology is O(n²) in point cloud size.** For n > 64 nodes, β₁ computation exceeds the 20 ms budget on RPi 4. The Snapdragon handles n = 128; beyond that, subsampling is required.

4. **ISRU Monitor uses synthetic thermodynamic data.** Real regolith/ice sensor fusion is not yet implemented. The Bayesian update framework is correct; the priors are placeholders.

5. **ROS2 bridge is single-threaded.** The executor runs in the same process as the control loop. For n > 16 nodes, run the bridge as a separate process and use shared memory IPC.

6. **Betti-1 Guard uses ripser, not GUDHI, for speed.** This means no cubical complex support — only Vietoris-Rips. For grid-based sensor coverage, use GUDHI directly (slower but more accurate).

---

## Citation

If you use SKN-V1 in your research, please cite:

```bibtex
@software{holland2026skn,
  author = {Holland, Chad},
  title = {SKN-V1: Sovereign Kinematic Node},
  url = {https://github.com/holland202/skn-v1-},
  version = {1.7.1},
  year = {2026},
  note = {Topology-aware swarm robotics with post-quantum trust}
}
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <sub>Built with rigor, not hype. v1.7.1 — July 2026</sub>
</p>

---

## Implementation status (honest map, 2026-07-20)

SKN-V1 is an active research framework. Some subsystems run and are tested today;
others are designed and described above but not yet implemented. This section is
the honest boundary so you know what executes on a fresh clone. Visuals and the
architecture narrative above describe the full **target** system.

**Implemented and tested** (`python tests/run_tests.py` → 15/15 passing):
- Natural-gradient kinematic formation control — converges (tetrahedron to
  0.0000 m formation error over 300 steps; verified in `skn/simulation_v3.py`).
- Propulsion allocator (HET + CMG) — output shape and actuator bounds tested.
- ISRU monitor — Gibbs-free-energy spontaneous/non-spontaneous filtering, tested.
- **Evidence Vault** — SHA3-512 tamper-evident hash chain. `verify_chain()` now
  genuinely recomputes every link and detects edited states, forged hashes, and
  reordered links (4 anti-vacuity tests). *Was previously vacuous; fixed and
  tested 2026-07-20.*
- Swarm gossip consensus — present in `skn/swarm.py`.

**Full detail on what's not implemented yet** (status is stated up front now, see
"What This Is" above — this section keeps the specifics): C-CPL post-quantum docking
needs ML-DSA-65 lattice signatures, not built. Betti-1 topology guard needs a
GUDHI/ripser backend, not built. ROS2 Humble bridge, not built. STM32F4 firmware
flashing, not built. Demo scripts: only `scripts/demo_formation.py` exists today;
`demo_rendezvous.py`, `demo_docking.py`, `demo_mission_control.py`, and
`flash_firmware.py` are planned.

The performance-dashboard timings (RPi4 / Snapdragon budgets) are design targets
for the full system, not measured benchmarks of the current code.

*Vincit Omnia Veritas — the vision is nine subsystems; today five run and are
tested, and this note says so plainly rather than letting the Quick Start fail
silently.*
