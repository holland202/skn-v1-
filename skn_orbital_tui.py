#!/usr/bin/env python3
"""SKN-V1 orbital dashboard, driven by the real code (2026-09-27).

Every value on screen comes from the skn package or from this device:
  - swarm map, formation error      skn.simulation_v3.formation_v3 (6 nodes into a ring), replayed step by step
  - pieces b0 / holes b1            skn.topology.betti at the communication radius, recomputed every frame
  - docking log                     skn.node.ccpl_initiate_dock (ML-DSA-65 signed) + skn.ccpl.verify_dock
  - evidence vault                  each node's EvidenceVault: depth, latest SHA3-512, verify_chain()
  - device                          /sys/class/thermal (hottest zone), load average, /proc/meminfo; "n/a" if unreadable
Nothing is random. The original look-alike with random data is kept in mockups/skn_orbital_tui_mockup.py.

  python skn_orbital_tui.py                 live dashboard (Ctrl+C to quit)
  python skn_orbital_tui.py --plain --frames 5   no ANSI, no sleep: prints frames as text (used by the tests)
SIMULATION ONLY: there is no hardware in this repository.
"""
import argparse, glob, math, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

from skn import ccpl  # noqa: E402
from skn.node import SKNV1_SovereignNode  # noqa: E402
from skn.simulation_v3 import formation_v3  # noqa: E402
from skn.topology import betti  # noqa: E402

G, C, W, R, Y, D, RESET = "\033[1;32m", "\033[1;36m", "\033[1;37m", "\033[1;31m", "\033[1;33m", "\033[1;30m", "\033[0m"
N, SCALE, STEPS, COMM_R = 6, 25.0, 300, 30.0
MAP_W, MAP_H = 45, 15


def device():
    """(hottest thermal zone in C or None, 1-min load or None, used/total GB or None)."""
    temps = []
    for f in glob.glob("/sys/class/thermal/thermal_zone*/temp"):
        try:
            v = int(open(f).read().strip()) / 1000
            if 0 < v < 150:
                temps.append(v)
        except (OSError, ValueError):
            pass
    try:
        load = os.getloadavg()[0]
    except (OSError, AttributeError):
        load = None
    mem = None
    try:
        info = dict(line.split(":", 1) for line in open("/proc/meminfo"))
        tot = int(info["MemTotal"].split()[0]) / 1048576
        avail = int(info["MemAvailable"].split()[0]) / 1048576
        mem = (tot - avail, tot)
    except (OSError, KeyError, ValueError):
        pass
    return (max(temps) if temps else None), load, mem


def dock_ring(P):
    """Dock each node to its ring neighbour with ML-DSA-65; returns (log lines, nodes)."""
    nodes = [SKNV1_SovereignNode(f"SKN-{i:03d}", np.r_[P[i], np.zeros(3)].astype(np.float32)) for i in range(len(P))]
    log, seen = [], set()
    if not ccpl.available():
        return ["ML-DSA-65 unavailable (pip install dilithium-py): docking fails closed, no locks"], nodes
    for i, a in enumerate(nodes):
        b = nodes[(i + 1) % len(nodes)]
        ok, detail = a.ccpl_initiate_dock(b.node_id, np.eye(3, dtype=np.float32), np.full(3, 0.2, np.float32))
        good = ccpl.verify_dock(a.last_dock_record, a.dock_public_key, seen)[0] if ok else False
        log.append(f"{a.node_id}->{b.node_id} {'LOCK' if ok else 'NO LOCK'}  sig {'VALID' if good else 'INVALID'}  {detail[:12]}")
    return log, nodes


def frame(k, hist, dock_log, nodes, plain):
    step, P, err = hist[min(k, len(hist) - 1)]
    col = (lambda c: "") if plain else (lambda c: c)
    rst = "" if plain else RESET
    b0, b1 = betti(P, COMM_R)
    temp, load, mem = device()
    out = [f"{col(W)}[ SKN-V1 // ORBITAL KINEMATICS // live from the skn package ]{rst}",
           f"{col(D)}simulation only, no hardware.  6 nodes -> ring, r_comm = {COMM_R:.0f} m{rst}", ""]
    grid = [[" "] * MAP_W for _ in range(MAP_H)]
    grid[MAP_H // 2][MAP_W // 2] = "+"
    lim = max(40.0, float(np.abs(P[:, :2]).max()) * 1.15)
    for i, (x, y, _) in enumerate(P):
        gx = int(round((x / lim + 1) / 2 * (MAP_W - 1)))
        gy = int(round((1 - (y / lim + 1) / 2) * (MAP_H - 1)))
        if 0 <= gx < MAP_W and 0 <= gy < MAP_H:
            grid[gy][gx] = str(i)
    left = [f"{col(C)}[FORMATION]{rst}",
            f" step   {step:>4} / {STEPS}",
            f" error  {err:12.6f} m",
            "",
            f"{col(C)}[TOPOLOGY GUARD]{rst}",
            f" pieces b0 = {b0}   {'(one swarm)' if b0 == 1 else '(FRAGMENTED)'}",
            f" holes  b1 = {b1}   {'(ring closed)' if b1 == 1 else ''}",
            "",
            f"{col(C)}[DEVICE]{rst}",
            f" temp  {'%.1f C' % temp if temp is not None else 'n/a'}",
            f" load  {'%.2f' % load if load is not None else 'n/a'}",
            f" mem   {'%.2f / %.2f GB' % mem if mem else 'n/a'}"]
    for i in range(max(len(left), MAP_H)):
        l = left[i] if i < len(left) else ""
        vis = len(l) - (len(col(C)) + len(rst) if l.startswith(col(C)) and col(C) else 0)
        m = "".join(grid[i]) if i < MAP_H else ""
        out.append(l + " " * max(1, 34 - vis) + (f"{col(D)}|{rst}{m}{col(D)}|{rst}" if i < MAP_H else ""))
    out.append("")
    if k >= len(hist) - 1:
        out.append(f"{col(C)}[C-CPL DOCKING, ML-DSA-65]{rst}")
        out += [" " + s for s in dock_log]
        v = nodes[0].vault
        out.append(f"{col(C)}[EVIDENCE VAULT {nodes[0].node_id}]{rst} depth {v.chain_length}  "
                   f"head {v.latest_hash.hex()[:16]}...  verify_chain {'OK' if v.verify_chain() else 'BROKEN'}")
    else:
        out.append(f"{col(D)}docking starts when the ring has formed{rst}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plain", action="store_true", help="no ANSI codes and no delay")
    ap.add_argument("--frames", type=int, default=None, help="stop after this many frames")
    ap.add_argument("--every", type=int, default=3, help="formation steps per frame")
    a = ap.parse_args()
    r = formation_v3(N, "ring", SCALE, STEPS, 0.05, verbose=False, record_every=a.every)
    hist = [(h["step"], np.array([h["poses"][k][:3] for k in sorted(h["poses"])]), h["formation_error"])
            for h in r["trajectory_history"]]
    dock_log, nodes = dock_ring(hist[-1][1])
    total = a.frames if a.frames is not None else len(hist) + 60
    if not a.plain:
        sys.stdout.write("\033[2J\033[?25l")
    try:
        for k in range(total):
            text = frame(k, hist, dock_log, nodes, a.plain)
            if a.plain:
                print(text + "\n")
            else:
                sys.stdout.write("\033[H" + text.replace("\n", "\033[K\n") + "\033[J")
                sys.stdout.flush()
                time.sleep(0.08)
    except KeyboardInterrupt:
        pass
    finally:
        if not a.plain:
            sys.stdout.write("\033[?25h\n")


if __name__ == "__main__":
    main()
