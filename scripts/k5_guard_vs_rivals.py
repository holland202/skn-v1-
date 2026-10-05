#!/usr/bin/env python3
"""k5_guard_vs_rivals.py - K5: what does the topology guard add over the standard connectivity checks?

  python scripts/k5_guard_vs_rivals.py              # registered run (docs/PREREG_2026-10-05b.md)
  python scripts/k5_guard_vs_rivals.py --sabotage   # betti links pairs closer than 1.2r; K5a/K5b must fail, exit 1

Exit 0 only if the outcome equals RECORDED (held predictions and digest).
"""
import hashlib
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import skn.topology as topo  # noqa: E402

R = 30.0
RECORDED = (("K5a", "K5b", "K5c", "K5d"), "1a1f89893705db7da7399192967889d9ef46b223464c111494d62663493d1acd")


def ring():
    a = np.radians(np.arange(0, 360, 60))
    return np.c_[20 * np.cos(a), 20 * np.sin(a), np.zeros(6)]


def signals(P):
    b0, b1 = topo.betti(P, R)
    return {"b0": b0, "b1": b1, "lam2": topo.algebraic_connectivity(P, R),
            "wlam2": topo.algebraic_connectivity(P, R, weighted=True), "m": topo.connectivity_margin(P, R)}


def trace(direction, steps):
    out = []
    for t in range(steps + 1):
        P = ring()
        P[0] += 0.1 * t * np.asarray(direction, dtype=float)
        out.append(signals(P))
    return out


def first(seq, pred):
    return next((i for i, s in enumerate(seq) if pred(s)), None)


def k5a():
    rng = np.random.default_rng(0)
    agree = 0
    for _ in range(500):
        n = int(rng.integers(3, 13))
        P = rng.uniform(0, 10, (n, 3))
        r = float(rng.uniform(1, 8))
        b0, _ = topo.betti(P, r)
        nullity = int(np.sum(topo.laplacian_spectrum(P, r) < 1e-9))
        uf = topo.components(P, r)
        m = topo.connectivity_margin(P, r)
        agree += (b0 == nullity == uf) and ((m > 0) == (b0 == 1))
    return agree


def main():
    sabotage = "--sabotage" in sys.argv
    if sabotage:
        real = topo.betti
        topo.betti = lambda P, r: real(P, 1.2 * r)
    print(f"K5 | {'SABOTAGE: betti uses 1.2r' if sabotage else 'registered run'} | python {sys.version.split()[0]}")
    v = {}
    agree = k5a()
    v["K5a"] = agree == 500
    print(f"  K5a 500 random clouds: b0 = Laplacian nullity = union-find, and m>0 <=> b0=1, in {agree} of 500")

    d1 = trace((1, 0, 0), 200)
    fb0 = first(d1, lambda s: s["b0"] > 1)
    fl = first(d1, lambda s: abs(s["lam2"] - d1[0]["lam2"]) > 1e-9)
    fb1 = first(d1, lambda s: s["b1"] != d1[0]["b1"])
    m = [s["m"] for s in d1]
    w = [s["wlam2"] for s in d1]
    m_dec = all(m[i + 1] < m[i] for i in range(145))
    w_noninc = all(w[i + 1] <= w[i] + 1e-12 for i in range(200))
    pred = 100 + m[100] / (m[99] - m[100])
    print(f"  K5b D1 radial: first b0>1 at {fb0}; first lam2 change at {fl}; first b1 change at {fb1}")
    print(f"      margin m: step0 {m[0]:.4f} step100 {m[100]:.4f} step144 {m[144]:.4f} step145 {m[145]:.4f};"
          f" strictly decreasing 0..145: {m_dec}")
    print(f"      weighted lam2: step0 {w[0]:.6f} step144 {w[144]:.3e} step145 {w[145]:.3e}; non-increasing: {w_noninc}")
    print(f"      step-100 extrapolation of m predicts fragmentation at step {pred:.1f}")
    v["K5b"] = (fb0 == 145 and fl == 145 and fb1 == 145 and m_dec and m[144] > 0 >= m[145] and w_noninc
                and w[144] > 0 and w[145] < 1e-9 and abs(pred - 145) <= 5)

    d2 = trace((0, 1, 0), 500)
    fb1 = first(d2, lambda s: s["b1"] != 1)
    fl = first(d2, lambda s: abs(s["lam2"] - 1.0) > 1e-9)
    fb0 = first(d2, lambda s: s["b0"] > 1)
    m = [s["m"] for s in d2]
    m10 = all(abs(x - 10) <= 1e-9 for x in m[:347])
    print(f"  K5c D2 sideways: b1 1->{d2[fb1]['b1'] if fb1 is not None else '-'} at {fb1};"
          f" lam2 1 -> {d2[fl]['lam2']:.6f} at {fl}; first b0>1 at {fb0}")
    print(f"      margin m = 10 for steps 0..346: {m10}; step347 {m[347]:.4f}; step456 {m[456]:.4f}; step457 {m[457]:.4f}")
    v["K5c"] = (fb1 == 110 and d2[110]["b1"] == 0 and fl == 110 and abs(d2[110]["lam2"] - 0.267949) <= 1e-6
                and fb0 == 457 and m10 and m[347] < 10)

    st = trace((0, 0, 0), 500)
    const = (all(s["b0"] == 1 and s["b1"] == 1 for s in st) and all(abs(s["lam2"] - 1) <= 1e-9 for s in st)
             and all(abs(s["m"] - 10) <= 1e-9 for s in st)
             and max(s["wlam2"] for s in st) - min(s["wlam2"] for s in st) <= 1e-12)
    print(f"  K5d static ring, 500 steps: every signal constant: {const}")
    v["K5d"] = const

    for k, ok in v.items():
        print(f"  {k}  {'HELD' if ok else 'REFUTED'}")
    held = tuple(k for k, ok in v.items() if ok)
    res = {"k5a": agree, "d1": [[s["b0"], s["b1"], round(s["lam2"], 6), round(s["m"], 6)] for s in d1],
           "d2": [[s["b0"], s["b1"], round(s["lam2"], 6), round(s["m"], 6)] for s in d2], "v": v}
    dg = hashlib.sha256(json.dumps(res, sort_keys=True).encode()).hexdigest()
    print(f"VERDICT {len(held)} of {len(v)} as registered (K5e is --sabotage)")
    print(f"DIGEST {dg}")
    if sabotage or RECORDED is None:
        return 0 if all(v.values()) else 1
    return 0 if (held, dg) == RECORDED else 1


if __name__ == "__main__":
    sys.exit(main())
