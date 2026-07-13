#!/usr/bin/env python3
"""SKN-V1 Formation Demo v3 — tetrahedron, cube, ring."""
from skn.simulation_v3 import formation_v3

for shape, n, scale in [("tetrahedron", 4, 20.0), ("cube", 8, 15.0), ("ring", 6, 25.0)]:
    result = formation_v3(n_nodes=n, shape=shape, scale=scale, n_steps=300, dt=0.05, verbose=False)
    print(f"{shape:12s} ({n} nodes): {result['final_error_m']:.4f}m")
