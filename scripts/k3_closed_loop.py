#!/usr/bin/env python3
"""k3_closed_loop.py - K3: move the node by what its thrusters realize, legacy vs paired geometry.

  python scripts/k3_closed_loop.py              # registered run (docs/PREREG_2026-10-05b.md)
  python scripts/k3_closed_loop.py --sabotage   # closed_loop ignored (pose moves by the command); K3b must fail, exit 1

K3f reads skn/node.py at 7510e5b with `git show`, so it needs the git history.
Exit 0 only if the outcome equals RECORDED (held predictions and digest).
"""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import skn.node as node_mod  # noqa: E402
from skn.node import PropulsionAllocator, SKNV1_SovereignNode  # noqa: E402

BASE = "7510e5b"
RECORDED = None


def base_node_class():
    try:
        src = subprocess.run(["git", "show", f"{BASE}:skn/node.py"], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"COULD NOT LOOK: cannot read skn/node.py at {BASE} ({exc}); fetch the history first")
        sys.exit(2)
    path = os.path.join(tempfile.mkdtemp(prefix="k3_"), "node_base.py")
    with open(path, "w") as fh:
        fh.write(src)
    spec = importlib.util.spec_from_file_location("node_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.SKNV1_SovereignNode


def run(target, steps, geometry, closed=True, clip=True):
    n = SKNV1_SovereignNode("K3", closed_loop=closed, thruster_geometry=geometry)
    if not clip:
        n.propulsion = PropulsionAllocator(geometry=geometry, clip=False)
    tgt = np.r_[np.asarray(target, dtype=float), np.zeros(3)]
    z = [float(n.pose[2])]
    for _ in range(steps):
        n.step(tgt)
        z.append(float(n.pose[2]))
    return n, z, float(np.linalg.norm(n.pose[:3] - tgt[:3]))


def main():
    sabotage = "--sabotage" in sys.argv
    if sabotage:
        real_init = node_mod.SKNV1_SovereignNode.__init__

        def init(self, *a, **k):
            real_init(self, *a, **k)
            self.closed_loop = False
        node_mod.SKNV1_SovereignNode.__init__ = init
    print(f"K3 | {'SABOTAGE: closed_loop ignored' if sabotage else 'registered run'} | python {sys.version.split()[0]}")
    v, res = {}, {}

    real = {}
    for g in ("legacy", "paired"):
        a = PropulsionAllocator(geometry=g)
        for sz in (-1, 1):
            real[(g, sz)] = a.realize(a.allocate(np.array([0, 0, sz, 0, 0, 0.0])))[:3].astype(float)
    exp = {("legacy", -1): (0, 0, 0), ("legacy", 1): (0, 0, 1.0), ("paired", -1): (0, 0, -0.5), ("paired", 1): (0, 0, 0.5)}
    v["K3a"] = all(np.allclose(real[k], exp[k], atol=1e-6) for k in exp)
    for k in exp:
        print(f"  K3a {k[0]:6s} command z={k[1]:+d}: realized translation {np.round(real[k], 6).tolist()}")
    res["K3a"] = {f"{k[0]}{k[1]}": np.round(real[k], 6).tolist() for k in exp}

    rng = np.random.default_rng(1)
    targets = rng.uniform(-10, 10, (50, 3))
    never_down, low_ok, low_n = True, True, 0
    for t in targets:
        _, z, _ = run(t, 1000, "legacy")
        never_down &= all(z[i + 1] >= z[i] for i in range(len(z) - 1))
        if t[2] < -1:
            low_n += 1
            low_ok &= abs(z[-1] - t[2]) >= abs(t[2])
    v["K3b"] = bool(never_down and low_ok)
    print(f"  K3b legacy, 50 targets x 1000 steps: z never decreased: {never_down};"
          f" {low_n} targets below z=-1, none got closer in z: {low_ok}")

    _, zp, dp = run((0, 0, -5), 1000, "paired")
    _, _, dl = run((0, 0, -5), 1000, "legacy")
    nonincr = all(zp[i + 1] <= zp[i] for i in range(1000))
    v["K3c"] = nonincr and dp < 1.0 and dl >= 5.0
    print(f"  K3c target (0,0,-5), 1000 steps: paired z non-increasing {nonincr}, final distance {dp:.4f} m;"
          f" legacy final distance {dl:.4f} m")
    res["K3c"] = [round(dp, 4), round(dl, 4)]

    ratios = []
    for t in targets:
        _, _, d = run(t, 3000, "paired")
        ratios.append(d / float(np.linalg.norm(t)))
    ok = sum(r < 0.5 for r in ratios)
    v["K3d"] = ok == 50
    print(f"  K3d paired, 50 targets x 3000 steps: final/initial distance < 0.5 in {ok} of 50"
          f" (max ratio {max(ratios):.4f}, median {float(np.median(ratios)):.4f})")
    res["K3d"] = [round(r, 4) for r in ratios]

    lr = [run(t, 3000, "legacy")[2] / float(np.linalg.norm(t)) for t in targets]
    print(f"  (unregistered) legacy, same 50 targets x 3000 steps: final/initial < 0.5 in "
          f"{sum(r < 0.5 for r in lr)} of 50 (median ratio {float(np.median(lr)):.4f}, max {max(lr):.4f})")

    gaps = {}
    for g in ("legacy", "paired"):
        nc, _, _ = run((5, -3, 2), 300, g, closed=True, clip=False)
        no, _, _ = run((5, -3, 2), 300, g, closed=False)
        gaps[g] = float(np.max(np.abs(nc.pose - no.pose)))
    v["K3e"] = all(x <= 1e-4 for x in gaps.values())
    print(f"  K3e clipping off, closed vs open loop, max pose difference after 300 steps: "
          f"legacy {gaps['legacy']:.2e}  paired {gaps['paired']:.2e}")

    Base = base_node_class()
    new, old = SKNV1_SovereignNode("K3f"), Base("K3f")
    tgt = np.array([5.0, -3.0, 2.0, 0, 0, 0])
    for _ in range(300):
        new.step(tgt)
        old.step(tgt)
    same = bool(np.array_equal(new.pose, old.pose))
    v["K3f"] = same
    print(f"  K3f default node vs {BASE}, 300 steps: poses identical {same} ({new.pose[:3].tolist()})")

    for k, ok in v.items():
        print(f"  {k}  {'HELD' if ok else 'REFUTED'}")
    held = tuple(k for k, ok in v.items() if ok)
    dg = hashlib.sha256(json.dumps({"r": res, "v": v}, sort_keys=True).encode()).hexdigest()
    print(f"VERDICT {len(held)} of {len(v)} as registered (K3g is --sabotage)")
    print(f"DIGEST {dg}")
    if sabotage or RECORDED is None:
        return 0 if all(v.values()) else 1
    return 0 if (held, dg) == RECORDED else 1


if __name__ == "__main__":
    sys.exit(main())
