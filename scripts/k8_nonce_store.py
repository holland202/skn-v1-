#!/usr/bin/env python3
"""k8_nonce_store.py - K8: does docking refuse when there is no nonce store? (docs/PREREG_2026-10-05c.md)

  python scripts/k8_nonce_store.py              # registered run
  python scripts/k8_nonce_store.py --sabotage   # skip-when-missing restored; exit 1 only if K8b is refuted. Control: --sabotage-noop (K8b holds, exit 0)

K8a reads skn/ccpl.py at ee573a3 with `git show`, so it needs the git history. Needs dilithium-py.
Exit 0 only if the outcome equals RECORDED (held predictions and digest).
"""
import ast
import copy
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
from skn import ccpl  # noqa: E402

BASE = "ee573a3"
RECORDED = (("K8a", "K8b", "K8c", "K8d"), "1e63fef0914ae1a2b271edd3dc446abf5fe7e3780b07caeda34a1b5c0a1d4f21")


def base_ccpl():
    try:
        src = subprocess.run(["git", "show", f"{BASE}:skn/ccpl.py"], cwd=ROOT, capture_output=True, text=True,
                             check=True).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"COULD NOT LOOK: cannot read skn/ccpl.py at {BASE} ({exc}); fetch the history first")
        sys.exit(2)
    path = os.path.join(tempfile.mkdtemp(prefix="k8_"), "ccpl_base.py")
    with open(path, "w") as fh:
        fh.write(src)
    spec = importlib.util.spec_from_file_location("ccpl_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sabotaged_verify(record, public_key, seen_nonces=None):
    """The pre-K8 rule: with no store, skip the replay check and accept."""
    ok, why = REAL_VERIFY(record, public_key, seen_nonces if seen_nonces is not None else set())
    return ok, why


REAL_VERIFY = ccpl.verify_dock


def short_calls():
    """verify_dock calls with fewer than three arguments in skn/, scripts/ and skn_orbital_tui.py."""
    files = [os.path.join(ROOT, "skn_orbital_tui.py")]
    for d in ("skn", "scripts"):
        files += [os.path.join(ROOT, d, f) for f in sorted(os.listdir(os.path.join(ROOT, d))) if f.endswith(".py")]
    hits = []
    for f in files:
        for node in ast.walk(ast.parse(open(f).read())):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "attr", getattr(node.func, "id", ""))
                if name == "verify_dock" and len(node.args) + len(node.keywords) < 3:
                    hits.append(f"{os.path.relpath(f, ROOT)}:{node.lineno}")
    return hits


def main():
    sabotage, noop = "--sabotage" in sys.argv, "--sabotage-noop" in sys.argv
    if sabotage or noop:
        ccpl.verify_dock = sabotaged_verify if sabotage else passthrough_verify
    print(f"K8 | {'SABOTAGE: missing store skips the replay check' if sabotage else 'SABOTAGE-NOOP: wrapper only' if noop else 'registered run'} | "
          f"python {sys.version.split()[0]}")
    if not ccpl.available():
        print("COULD NOT LOOK: dilithium-py is not installed")
        return 2
    pk, sk = ccpl.keygen()
    opk, _ = ccpl.keygen()
    m = ccpl.make_manifest("SKN-001", "SKN-002", np.zeros(6), np.eye(3).ravel(), np.full(3, 0.2))
    rec = ccpl.sign_manifest(m, pk, sk)
    v, res = {}, {}

    old = base_ccpl()
    a = (old.verify_dock(rec, pk)[0], old.verify_dock(rec, pk)[0])
    v["K8a"] = a == (True, True)
    print(f"  K8a code at {BASE}, genuine record twice, no store: {a}")
    res["K8a"] = list(a)

    b1, b2 = ccpl.verify_dock(rec, pk), ccpl.verify_dock(rec, pk)
    seen = set()
    s1, s2 = ccpl.verify_dock(rec, pk, seen), ccpl.verify_dock(rec, pk, seen)
    v["K8b"] = (b1 == b2 == (False, "no nonce store: replay cannot be checked (fail closed)") and s1[0] is True
                and s2 == (False, "nonce already seen (replay)"))
    print(f"  K8b fix, no store, twice: {b1} {b2}")
    print(f"      with a store: {s1} then {s2}")
    res["K8b"] = [list(b1), list(b2), list(s1), list(s2)]

    bad = copy.deepcopy(rec)
    bad["manifest"]["target_id"] = "SKN-666"
    bad["manifest_sha3_512"] = hashlib.sha3_512(ccpl.canonical(bad["manifest"])).hexdigest()
    c1 = ccpl.verify_dock(bad, pk)[1]
    c2 = ccpl.verify_dock(rec, opk)[1]
    broken = {k: x for k, x in rec.items() if k != "signature"}
    c3 = ccpl.verify_dock(broken, pk)[1]
    v["K8c"] = (c1 == "signature does not verify" and c2 == "record names a different public key"
                and c3.startswith("malformed record"))
    print(f"  K8c no store: tampered -> {c1!r}; other key -> {c2!r}; missing field -> {c3!r}")
    res["K8c"] = [c1, c2, c3]

    seen = set()
    r = [ccpl.verify_dock(bad, pk, seen)[0], ccpl.verify_dock(rec, opk, seen)[0], ccpl.verify_dock(broken, pk, seen)[0]]
    empty = len(seen)
    after = ccpl.verify_dock(rec, pk, seen)[0]
    v["K8d"] = r == [False, False, False] and empty == 0 and after is True
    print(f"  K8d shared store: refusals {r}, store size after them {empty}, genuine afterwards {after}")
    res["K8d"] = [r, empty, after]

    hits = short_calls()
    demo = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "demo_30s.py")], capture_output=True,
                          text=True, cwd=ROOT)
    tui = subprocess.run([sys.executable, os.path.join(ROOT, "skn_orbital_tui.py"), "--plain", "--frames", "101"],
                         capture_output=True, text=True, cwd=ROOT, timeout=600)
    valid = tui.stdout.strip().split("[ SKN-V1")[-1].count("sig VALID")
    demo_ok = demo.returncode == 0 and "DEMO PASS" in demo.stdout
    v["K8e"] = hits == [] and demo_ok and valid == 6
    print(f"  K8e calls without a store: {hits}; demo_30s DEMO PASS: {demo_ok}; dashboard sig VALID: {valid} of 6")
    res["K8e"] = [hits, demo_ok, valid]
    others = [h for h in hits if not h.startswith("scripts/k8_nonce_store.py")]
    print(f"  (unregistered, added after the first run) the same scan excluding this harness's own deliberate "
          f"no-store calls: {others}")

    for k, ok in v.items():
        print(f"  {k}  {'HELD' if ok else 'REFUTED'}")
    held = tuple(k for k, ok in v.items() if ok)
    dg = hashlib.sha256(json.dumps({"r": res, "v": v}, sort_keys=True).encode()).hexdigest()
    print(f"VERDICT {len(held)} of {len(v)} as registered (K8f is --sabotage)")
    print(f"DIGEST {dg}")
    if sabotage:
        return 1 if not v["K8b"] else 0   # exit 1 only because K8b is refuted
    if noop:
        return 0 if v["K8b"] else 1       # control: same patching path, K8b must hold
    if RECORDED is None:
        return 0 if all(v.values()) else 1
    return 0 if (held, dg) == RECORDED else 1


def passthrough_verify(record, public_key, seen_nonces=None):
    """Control: the same wrapper shape as sabotaged_verify, with the one behaviour under test left alone."""
    return REAL_VERIFY(record, public_key, seen_nonces)


if __name__ == "__main__":
    sys.exit(main())
