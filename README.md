# SKN-V1 — Sovereign Kinematic Node

> Topology-aware, cryptographically sovereign swarm platform unifying kinematics, information geometry, and post-quantum trust for deep-space operations.

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)]()
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)]()
[![License](https://img.shields.io/badge/license-MIT-lightgrey)]()

## What This Is

SKN-V1 is a **software-defined swarm robotics framework** that runs on anything from a Raspberry Pi to a Snapdragon-class edge device. It implements:

- **Natural Gradient Kinematic Control** — SE(3) pose tracking on the Fisher-Rao information manifold
- **Riemannian Gossip Consensus** — KL-divergence minimization with adaptive Fisher metrics
- **C-CPL Cryptographic Docking** — Post-quantum manifest binding (ML-DSA-65 ready)
- **Evidence Vault** — SHA3-512 tamper-evident hash chain with per-state attestation
- **ISRU Monitor** — Gibbs free energy filtering for resource extraction
- **Betti-1 Topology Guard** — Real-time persistent homology for swarm health

## Quick Start

```bash
git clone https://github.com/holland202/skn-v1-.git
cd skn-v1-
pip install -e .
python tests/run_tests.py        # 11 tests, all passing
python scripts/demo_formation.py # Tetrahedron/cube/ring convergence
