#!/usr/bin/env python3
"""The 30-second demo, text only: formation, topology guard, signed docking, attacks, evidence chain.

  pip install -e . dilithium-py && python scripts/demo_30s.py

SIMULATION ONLY: no hardware. Every value is computed by skn in this run. Exit 0 only if every line
comes out as expected, so the demo is itself a check that can fail.
"""
import copy, hashlib, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np  # noqa: E402
from skn import ccpl  # noqa: E402
from skn.node import SKNV1_SovereignNode  # noqa: E402
from skn.simulation_v3 import formation_v3  # noqa: E402
from skn.topology import betti  # noqa: E402

ok = True


def line(good, text):
    global ok
    ok &= bool(good)
    print(f"{'ok ' if good else 'BAD'} {text}")


t = time.perf_counter()
r = formation_v3(6, "ring", 25.0, 300, 0.05, verbose=False, record_every=1)
P = np.array([r["trajectory_history"][-1]["poses"][k][:3] for k in sorted(r["trajectory_history"][-1]["poses"])])
line(r["final_error_m"] < 1e-4, f"6 nodes -> ring in 300 steps: final formation error {r['final_error_m']:.2e} m "
     f"({1000 * (time.perf_counter() - t):.0f} ms)")
b0, b1 = betti(P, 30.0)
line((b0, b1) == (1, 1), f"topology guard at r = 30 m: pieces b0 = {b0}, holes b1 = {b1} (one ring)")
b0s, b1s = betti(P[:3], 30.0)
line(b1s == 0, f"same guard on 3 of the 6 nodes: b0 = {b0s}, b1 = {b1s} (the ring is broken)")

if not ccpl.available():
    line(False, "ML-DSA-65 unavailable: pip install dilithium-py (docking fails closed)")
else:
    a = SKNV1_SovereignNode("SKN-001", np.zeros(6, np.float32))
    b = SKNV1_SovereignNode("SKN-002", np.zeros(6, np.float32))
    b.ccpl_initiate_dock("SKN-001", np.eye(3, dtype=np.float32), np.full(3, 0.2, np.float32))
    t = time.perf_counter()
    locked, _ = a.ccpl_initiate_dock("SKN-002", np.eye(3, dtype=np.float32), np.full(3, 0.2, np.float32))
    ms = 1000 * (time.perf_counter() - t)
    rec, pk, seen = a.last_dock_record, a.dock_public_key, set()
    line(locked and ccpl.verify_dock(rec, pk, seen)[0], f"signed dock SKN-001 -> SKN-002 verified (keygen + sign {ms:.0f} ms)")
    bad = copy.deepcopy(rec); bad["manifest"]["target_id"] = "SKN-666"
    bad["manifest_sha3_512"] = hashlib.sha3_512(ccpl.canonical(bad["manifest"])).hexdigest()
    res = ccpl.verify_dock(bad, pk)
    line(not res[0], f"target changed, digest recomputed: refused ({res[1]})")
    res = ccpl.verify_dock(rec, b.dock_public_key)
    line(not res[0], f"another node's key: refused ({res[1]})")
    res = ccpl.verify_dock(rec, pk, seen)
    line(not res[0], f"same nonce replayed: refused ({res[1]})")

v = SKNV1_SovereignNode("SKN-003", np.zeros(6, np.float32)).vault
for i in range(10):
    v.commit(np.random.default_rng(i).standard_normal(7).astype(np.float32), {"i": i})
line(v.verify_chain(), f"evidence chain: {v.chain_length} SHA3-512 records verify")
v._records[3], v._records[4] = v._records[4], v._records[3]
line(not v.verify_chain(), "two records swapped: chain refuses")
print("DEMO", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
