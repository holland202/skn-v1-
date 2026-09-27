"""Timing for the topology guard and ML-DSA-65 docking on this machine. Prints the median of repeats."""
import sys, os, time, platform, statistics
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # run from a checkout without pip install
import numpy as np
from skn.topology import betti
from skn import ccpl


def med(f, k):
    ts = []
    for _ in range(k):
        t = time.perf_counter(); f(); ts.append(time.perf_counter() - t)
    return 1000 * statistics.median(ts)


print(f"{platform.machine()} | Python {platform.python_version()}")
from skn.node import SKNV1_SovereignNode
_node, _tgt = SKNV1_SovereignNode("BENCH", np.full(6, 10, np.float32)), np.zeros(6, np.float32)
print(f"control step (one node.step, incl. vault commit): {med(lambda: _node.step(_tgt, 0.05), 200):.3f} ms")
rng = np.random.default_rng(0)
for n in (4, 8, 16, 32, 64):
    P = rng.uniform(0, 10, (n, 3))
    print(f"betti, n={n:>2}, r=4: {med(lambda: betti(P, 4.0), 5):8.2f} ms   (b0, b1) = {betti(P, 4.0)}")
if ccpl.available():
    pk, sk = ccpl.keygen()
    m = ccpl.make_manifest("A", "B", np.zeros(6), np.eye(3).ravel(), np.zeros(3))
    rec = ccpl.sign_manifest(m, pk, sk)
    print(f"ML-DSA-65 keygen {med(ccpl.keygen, 5):.2f} ms, sign {med(lambda: ccpl.sign_manifest(m, pk, sk), 5):.2f} ms, "
          f"verify {med(lambda: ccpl.verify_dock(rec, pk), 5):.2f} ms  (dilithium-py, pure Python)")
else:
    print("ML-DSA-65: dilithium-py not installed")
