#!/usr/bin/env python3
"""k4_vault_window.py - K4: does the evidence vault's check stay honest past its 256-record window?

  python scripts/k4_vault_window.py              # registered run (docs/PREREG_2026-10-05.md)
  python scripts/k4_vault_window.py --sabotage   # verify_chain starts from genesis again; V2/V5 must fail, exit 1

V1 runs the vault exactly as it was at 117f08f (read with `git show`, so it needs the git history).
Exit 0 only if every registered prediction holds (exit 1 otherwise; 2 = could not run).
"""
import importlib.util
import os
import subprocess
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from skn.node import EvidenceVault, SKNV1_SovereignNode  # noqa: E402

LEGACY = "117f08f"


def legacy_vault_class():
    try:
        src = subprocess.run(["git", "show", f"{LEGACY}:skn/node.py"], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"COULD NOT LOOK: cannot read skn/node.py at {LEGACY} ({exc}); fetch the history first")
        sys.exit(2)
    path = os.path.join(tempfile.mkdtemp(prefix="k4_"), "node_legacy.py")
    with open(path, "w") as fh:
        fh.write(src)
    spec = importlib.util.spec_from_file_location("node_legacy", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.EvidenceVault


def filled(cls, n):
    v = cls()
    for i in range(n):
        v.commit(np.full(6, float(i)), {"i": i})
    return v


def genesis_verify(self):
    """The pre-K4 rule: the retained window must start at the all-zero genesis hash."""
    expected = b"\x00" * 64
    import hashlib
    for rec in self._records:
        if rec["prev"] != expected or hashlib.sha3_512(rec["preimage"] + rec["prev"]).digest() != rec["hash"]:
            return False
        expected = rec["hash"]
    return True


def main():
    sabotage = "--sabotage" in sys.argv
    if sabotage:
        EvidenceVault.verify_chain = genesis_verify
    print(f"K4 | {'SABOTAGE: verify_chain starts from genesis' if sabotage else 'registered run'} | "
          f"python {sys.version.split()[0]}")
    Legacy = legacy_vault_class()
    r = {}
    r["V1"] = filled(Legacy, 257).verify_chain() is False
    v2 = {n: filled(EvidenceVault, n).verify_chain() for n in (10, 256, 257, 1000)}
    r["V2"] = all(v2.values())
    t = {}
    v = filled(EvidenceVault, 1000)
    v._records[100]["preimage"] = v._records[100]["preimage"] + b"x"
    t["edit preimage"] = v.verify_chain()
    v = filled(EvidenceVault, 1000)
    v._records[50], v._records[51] = v._records[51], v._records[50]
    t["swap two records"] = v.verify_chain()
    v = filled(EvidenceVault, 1000)
    v._records[200]["hash"] = b"\x01" * 64
    t["replace a hash"] = v.verify_chain()
    r["V3"] = not any(t.values())
    v = filled(EvidenceVault, 1000)
    v._anchor = b"\x02" * 64
    r["V4"] = v.verify_chain() is False
    node = SKNV1_SovereignNode("SKN-K4")
    target = np.array([5.0, -3.0, 2.0, 0.0, 0.0, 0.0])
    for _ in range(300):
        node.step(target)
    v5 = node.vault.verify_chain()
    r["V5"] = v5 is True
    print(f"  V1 legacy vault, 257 commits: verify_chain {filled(Legacy, 257).verify_chain()}")
    print(f"  V2 fixed vault: {v2}")
    print(f"  V3 tampering at 1000 commits, verify_chain per attack: {t}")
    print(f"  V4 altered anchor at 1000 commits: verify_chain {not r['V4']}")
    print(f"  V5 node after 300 steps: verify_chain {v5}, chain_length {node.vault.chain_length}")
    for k, ok in r.items():
        print(f"  {k}  {'HELD' if ok else 'REFUTED'}")
    print(f"VERDICT {sum(r.values())} of {len(r)} as registered (V6 is --sabotage)")
    return 0 if all(r.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
