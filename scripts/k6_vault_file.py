#!/usr/bin/env python3
"""k6_vault_file.py - K6: does the vault file keep dropped records checkable, and what does it miss?

  python scripts/k6_vault_file.py              # registered run (docs/PREREG_2026-10-05b.md)
  python scripts/k6_vault_file.py --sabotage   # verify_file checks prev links only; K6b must fail, exit 1

Hashes include time.time_ns(), so the digest covers outcomes and counts only.
Exit 0 only if the outcome equals RECORDED (held predictions and digest).
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from skn.node import EvidenceVault  # noqa: E402

RECORDED = None


def fill(v, n, start=0):
    for i in range(start, start + n):
        v.commit(np.full(6, float(i)), {"i": i})


def lines(path):
    with open(path) as fh:
        return fh.readlines()


def write(path, ls):
    with open(path, "w") as fh:
        fh.writelines(ls)


def variant(src, dst, fn):
    ls = lines(src)
    write(dst, fn(ls))
    return EvidenceVault.verify_file(dst)


def main():
    sabotage = "--sabotage" in sys.argv
    if sabotage:
        EvidenceVault.verify_file = staticmethod(lambda p: EvidenceVault._walk_file(p, check_hashes=False)[0])
    print(f"K6 | {'SABOTAGE: verify_file checks prev links only' if sabotage else 'registered run'} | "
          f"python {sys.version.split()[0]}")
    d = tempfile.mkdtemp(prefix="k6_")
    base = os.path.join(d, "vault.jsonl")
    v = {}
    vault = EvidenceVault(base)
    fill(vault, 1000)
    n_lines, ok_a = len(lines(base)), EvidenceVault.verify_file(base)
    v["K6a"] = n_lines == 1000 and ok_a
    print(f"  K6a 1000 commits: file lines {n_lines}, verify_file {ok_a}")

    def edit10(ls):
        rec = json.loads(ls[9])
        rec["preimage"] = rec["preimage"][:-2] + ("00" if rec["preimage"][-2:] != "00" else "01")
        ls[9] = json.dumps(rec) + "\n"
        return ls
    tampered = os.path.join(d, "edit10.jsonl")
    ok_b = variant(base, tampered, edit10)
    mem = vault.verify_chain()
    v["K6b"] = (not ok_b) and mem
    print(f"  K6b preimage edited on line 10: verify_file {ok_b}; in-memory verify_chain {mem} "
          f"(memory holds the newest {vault.chain_length})")

    del500 = variant(base, os.path.join(d, "del500.jsonl"), lambda ls: ls[:499] + ls[500:])
    swap = variant(base, os.path.join(d, "swap.jsonl"), lambda ls: ls[:299] + [ls[300], ls[299]] + ls[301:])
    v["K6c"] = (not del500) and (not swap)
    print(f"  K6c line 500 deleted: verify_file {del500}; lines 300/301 swapped: verify_file {swap}")

    trunc = variant(base, os.path.join(d, "trunc.jsonl"), lambda ls: ls[:-1])
    v["K6d"] = trunc
    print(f"  K6d last line deleted (tail truncation): verify_file {trunc}  <- registered as NOT detected")

    resumed = os.path.join(d, "resume.jsonl")
    shutil.copy(base, resumed)
    v2 = EvidenceVault(resumed)
    fill(v2, 500, start=1000)
    n2, ok_e = len(lines(resumed)), EvidenceVault.verify_file(resumed)
    try:
        EvidenceVault(tampered)
        refused = False
    except ValueError:
        refused = True
    v["K6e"] = n2 == 1500 and ok_e and v2.verify_chain() and refused
    print(f"  K6e resumed vault +500: file lines {n2}, verify_file {ok_e}, verify_chain {v2.verify_chain()};"
          f" opening the tampered file refused: {refused}")

    before = set(os.listdir(d)) | set(os.listdir(os.getcwd()))
    v3 = EvidenceVault()
    fill(v3, 300)
    after = set(os.listdir(d)) | set(os.listdir(os.getcwd()))
    v["K6f"] = before == after and v3.verify_chain()
    print(f"  K6f no path, 300 commits: new files created {sorted(after - before)}, verify_chain {v3.verify_chain()}")
    shutil.rmtree(d)

    for k, ok in v.items():
        print(f"  {k}  {'HELD' if ok else 'REFUTED'}")
    held = tuple(k for k, ok in v.items() if ok)
    dg = hashlib.sha256(json.dumps({"v": v, "n": [n_lines, n2]}, sort_keys=True).encode()).hexdigest()
    print(f"VERDICT {len(held)} of {len(v)} as registered (K6g is --sabotage; K6f's 'existing tests pass' is CI)")
    print(f"DIGEST {dg}")
    if sabotage or RECORDED is None:
        return 0 if all(v.values()) else 1
    return 0 if (held, dg) == RECORDED else 1


if __name__ == "__main__":
    sys.exit(main())
