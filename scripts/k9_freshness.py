#!/usr/bin/env python3
"""k9_freshness.py - K9: the signed manifest time is never checked (docs/PREREG_2026-10-05d.md)

  python scripts/k9_freshness.py              # registered run
  python scripts/k9_freshness.py --sabotage   # check_fresh always accepts; P2 must be REFUTED, exit 1

Needs dilithium-py. Exit 0 only if the outcome equals RECORDED (held predictions and digest).
"""
import hashlib
import json
import math
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from skn import ccpl  # noqa: E402

RECORDED = None

T0 = 1_800_000_000.0
N_ORDER = 1000
N_AFTER = 100
MAX_SKEW = 5.0
STALE = 3600
FUTURE = 86400

REAL_CHECK = ccpl.check_fresh


def sabotaged_check(manifest, key_fp, marks, now, max_skew=None):
    return True, "fresh (SABOTAGE)"


class Signer:
    def __init__(self):
        self.pk, self.sk = ccpl.keygen()
        self.n = 0

    def record(self, t):
        self.n += 1
        m = ccpl.make_manifest("SKN-001", "SKN-002", np.zeros(6), np.eye(3).ravel(), np.full(3, 0.2),
                               nonce=f"{self.n:032x}", t=t)
        return ccpl.sign_manifest(m, self.pk, self.sk)


def dock(rec, pk, seen, marks, now, max_skew=None):
    """Registered composition: integrity and signature, then nonce (no add), then check_fresh,
    then commit nonce and mark. verify_dock runs on a copy of the store so it cannot add the nonce early."""
    ok, why = ccpl.verify_dock(rec, pk, set(seen))
    if not ok:
        return False, why
    fp = rec["public_key_sha3_256"]
    ok, why = ccpl.check_fresh(rec["manifest"], fp, marks, now, max_skew)
    if not ok:
        return False, why
    seen.add(rec["manifest"]["nonce"])
    marks[fp] = rec["manifest"]["time"]
    return True, why


def lr_maxima(xs):
    best, n = -math.inf, 0
    for x in xs:
        if x > best:
            best, n = x, n + 1
    return n


def main():
    sabotage = "--sabotage" in sys.argv
    if sabotage:
        ccpl.check_fresh = sabotaged_check
    print(f"K9 | {'SABOTAGE: check_fresh always accepts' if sabotage else 'registered run'} | "
          f"python {sys.version.split()[0]} | T0={T0} N_ORDER={N_ORDER} N_AFTER={N_AFTER} MAX_SKEW={MAX_SKEW}")
    if not ccpl.available():
        print("COULD NOT LOOK: dilithium-py is not installed")
        return 2
    s = Signer()
    pk = s.pk
    v, res = {}, {}

    # P1: the hole at base. verify_dock alone, empty store, an hour-old genuine record.
    p1 = ccpl.verify_dock(s.record(T0 - STALE), pk, set())
    v["P1"] = p1[0] is True
    res["P1"] = list(p1)
    print(f"  P1 verify_dock, record at T0-{STALE}, empty store: {p1}")

    # P2: the mark refuses old and equal times.
    fp = s.record(T0)["public_key_sha3_256"]
    seen, marks = set(), {fp: T0}
    a = dock(s.record(T0 - STALE), pk, seen, marks, T0)
    b = dock(s.record(T0), pk, seen, marks, T0)
    c = dock(s.record(T0 + 1), pk, seen, marks, T0)
    v["P2"] = (a[0] is False and b[0] is False and c[0] is True and marks[fp] == T0 + 1
               and "mark" in a[1] and "mark" in b[1])
    res["P2"] = [list(a), list(b), list(c), marks[fp]]
    print(f"  P2 mark=T0: T0-{STALE} -> {a}; T0 -> {b}; T0+1 -> {c}; mark after {marks[fp]}")

    # P3: out-of-order delivery.
    recs = [s.record(T0 + 0.1 * i) for i in range(N_ORDER)]
    seen, marks = set(), {}
    in_order = sum(dock(r, pk, seen, marks, T0)[0] for r in recs)
    perm = np.random.default_rng(0).permutation(N_ORDER)
    seen, marks = set(), {}
    shuffled = sum(dock(recs[i], pk, seen, marks, T0)[0] for i in perm)
    lrm = lr_maxima([int(i) for i in perm])
    harmonic = sum(1.0 / k for k in range(1, N_ORDER + 1))
    v["P3"] = in_order == N_ORDER and shuffled == lrm and shuffled <= 20
    res["P3"] = [in_order, shuffled, lrm]
    print(f"  P3 in order {in_order}/{N_ORDER}; shuffled (seed 0) {shuffled}/{N_ORDER}; "
          f"left-to-right maxima {lrm}; H_{N_ORDER} = {harmonic:.4f}")

    # P4: a future-dated record locks the key out. now = T0 as registered.
    after = [s.record(T0 + j) for j in range(1, N_AFTER + 1)]
    arms = {}
    for name, skew in (("no_skew", None), ("max_skew", MAX_SKEW)):
        seen, marks = set(), {}
        fut = dock(s.record(T0 + FUTURE), pk, seen, marks, T0, skew)
        acc = sum(dock(r, pk, seen, marks, T0, skew)[0] for r in after)
        arms[name] = [fut[0], acc]
        print(f"  P4 {name}: future record at T0+{FUTURE} accepted {fut[0]}; then {acc}/{N_AFTER} legitimate accepted")
    v["P4"] = arms["no_skew"] == [True, 0] and arms["max_skew"] == [False, N_AFTER]
    res["P4"] = arms
    # Unregistered diagnostic, added before the first run once the registration error was seen in review:
    # the same max_skew arm with now = T0 + N_AFTER. Not part of P4 or the digest.
    seen, marks = set(), {}
    dfut = dock(s.record(T0 + FUTURE), pk, seen, marks, T0 + N_AFTER, MAX_SKEW)
    dacc = sum(dock(r, pk, seen, marks, T0 + N_AFTER, MAX_SKEW)[0] for r in after)
    print(f"  (unregistered diagnostic) max_skew with now=T0+{N_AFTER}: future accepted {dfut[0]}; "
          f"then {dacc}/{N_AFTER} legitimate accepted")

    # P5: non-finite and non-numeric times.
    nan = float("nan")
    naive = not (nan <= T0)
    rows = []
    for label, t in (("NaN", nan), ("inf", float("inf")), ('"1"', "1"), ("True", True)):
        try:
            r = s.record(t)
            ok_sig = ccpl.verify_dock(r, pk, set())[0]
        except (ValueError, TypeError) as exc:
            rows.append([label, "UNREACHABLE", type(exc).__name__])
            continue
        seen, marks = set(), {r["public_key_sha3_256"]: T0}
        out = dock(r, pk, seen, marks, T0)
        rows.append([label, "signature valid" if ok_sig else "signature invalid", out[0], out[1]])
    reachable = [x for x in rows if x[1] != "UNREACHABLE"]
    refused = sum(1 for x in reachable if x[2] is False)
    v["P5"] = naive and len(reachable) > 0 and refused == len(reachable)
    res["P5"] = [naive, rows]
    print(f"  P5 naive 'NaN <= mark' is False, so a naive check accepts NaN: {naive}")
    for x in rows:
        print(f"     time {x[0]}: {x[1:]}")
    print(f"     refused {refused} of {len(reachable)} reachable ({len(rows) - len(reachable)} unreachable)")

    # P6: K8 and earlier behaviour unchanged.
    t = subprocess.run([sys.executable, os.path.join(ROOT, "tests", "run_tests.py")], capture_output=True,
                       text=True, cwd=ROOT)
    tests_ok = t.returncode == 0
    r = s.record(T0 + 5000)
    seen, marks = set(), {}
    first, again = dock(r, pk, seen, marks, T0), dock(r, pk, seen, marks, T0)
    stale = s.record(T0 - STALE)
    seen, marks = set(), {stale["public_key_sha3_256"]: T0}
    st = dock(stale, pk, seen, marks, T0)
    nonce_kept = stale["manifest"]["nonce"] in seen
    v["P6"] = (tests_ok and first[0] is True and again == (False, "nonce already seen (replay)")
               and st[0] is False and not nonce_kept)
    res["P6"] = [tests_ok, list(first), list(again), list(st), nonce_kept]
    print(f"  P6 tests/run_tests.py exit 0: {tests_ok}; replay: {first} then {again}; "
          f"stale refused {st}, its nonce added to the store: {nonce_kept}")

    for k, ok in v.items():
        print(f"  {k}  {'HELD' if ok else 'REFUTED'}")
    held = tuple(k for k, ok in v.items() if ok)
    dg = hashlib.sha256(json.dumps({"r": res, "v": v}, sort_keys=True).encode()).hexdigest()
    print(f"VERDICT {len(held)} of {len(v)} as registered (P7 is --sabotage)")
    print(f"DIGEST {dg}")
    if sabotage:
        # P7: the mechanism's absence must refute P2 specifically, not just any prediction.
        print(f"  P7  {'HELD' if not v['P2'] else 'REFUTED'} (sabotage refutes P2: {not v['P2']})")
        return 1 if not v["P2"] else 0
    if RECORDED is None:
        return 0
    return 0 if (held, dg) == RECORDED else 1


if __name__ == "__main__":
    sys.exit(main())
