#!/usr/bin/env python3
"""SKN-V1 visual demo: everything on screen is computed by skn in this run. Nothing is drawn by hand.

  python scripts/demo_visual.py [--out assets/skn_demo] [--fps 12]

Writes <out>.gif (and <out>.mp4 when ffmpeg is present). Three acts:
  1. Formation: 6 nodes converge from random poses into a ring (skn.simulation_v3.formation_v3).
     Each frame prints the formation error and the topology guard's Betti numbers at the communication
     radius (skn.topology), next to the old graph count it replaced.
  2. Signed docking: two nodes dock; the ML-DSA-65 record is verified live (skn.ccpl).
  3. Attacks on that record: a changed field, another node's key and a replay are refused.
SIMULATION ONLY: there is no hardware in this repository.
"""
import sys, os, copy, time, argparse, shutil, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # run from a checkout without pip install
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

from skn.simulation_v3 import formation_v3
from skn.topology import betti, graph_cycle_rank
from skn import ccpl
from skn.node import SKNV1_SovereignNode

BG, FG, DIM, BLUE, ORANGE, GREEN, RED = "#0b1016", "#e8edf3", "#8b9bb0", "#5fb3ff", "#f0a04b", "#3cc48d", "#e98b8b"


def formation_frames(n=6, scale=25.0, steps=300, every=3):
    r = formation_v3(n, "ring", scale, steps, 0.05, verbose=False, record_every=every)
    frames = []
    for h in r["trajectory_history"]:
        P = np.array([h["poses"][k][:3] for k in sorted(h["poses"])])
        frames.append((h["step"], P, h["formation_error"]))
    return frames, r


def dock_story():
    """Run the real dock and the three attacks; return the lines to show."""
    if not ccpl.available():
        return ["ML-DSA-65 unavailable: pip install dilithium-py", "docking fails closed: no lock"], []
    a = SKNV1_SovereignNode("SKN-001", np.zeros(6, np.float32))
    b = SKNV1_SovereignNode("SKN-002", np.zeros(6, np.float32))
    b.ccpl_initiate_dock("SKN-001", np.eye(3, dtype=np.float32), np.full(3, 0.2, np.float32))  # b has a key
    t = time.perf_counter()
    ok, digest = a.ccpl_initiate_dock("SKN-002", np.eye(3, dtype=np.float32), np.full(3, 0.2, np.float32))
    ms = 1000 * (time.perf_counter() - t)
    rec, pk = a.last_dock_record, a.dock_public_key
    seen = set()
    genuine = ccpl.verify_dock(rec, pk, seen)
    bad = copy.deepcopy(rec); bad["manifest"]["target_id"] = "SKN-666"
    tamper = ccpl.verify_dock(bad, pk, seen)
    wrongkey = ccpl.verify_dock(rec, b.dock_public_key, seen)
    replay = ccpl.verify_dock(rec, pk, seen)
    return [
        f"SKN-001 -> SKN-002  locked={ok}",
        f"keygen + sign + lock  {ms:.0f} ms (pure Python)",
        f"manifest SHA3-512  {digest[:24]}...",
        f"signature  ML-DSA-65, {len(rec['signature']) // 2} bytes",
        "",
        f"genuine record       {'VALID' if genuine[0] else 'REFUSED'}",
        f"target_id changed    {'VALID' if tamper[0] else 'REFUSED'}",
        f"another node's key   {'VALID' if wrongkey[0] else 'REFUSED'}",
        f"same nonce replayed  {'VALID' if replay[0] else 'REFUSED'}",
    ], [genuine[1], tamper[1], wrongkey[1], replay[1]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="assets/skn_demo")
    ap.add_argument("--fps", type=int, default=10)
    a = ap.parse_args()
    frames, res = formation_frames()
    comm_r = 30.0  # neighbours on the 25 m ring are 25 m apart; the opposite side is 50 m away
    story, reasons = dock_story()
    hold_form, hold_dock = 18, 42
    total = len(frames) + hold_form + hold_dock

    plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": FG, "axes.labelcolor": DIM,
                         "xtick.color": DIM, "ytick.color": DIM})
    fig = plt.figure(figsize=(9.6, 5.4), dpi=90, facecolor=BG)
    ax3 = fig.add_axes([0.0, 0.08, 0.55, 0.80], projection="3d", facecolor=BG)
    axe = fig.add_axes([0.62, 0.52, 0.34, 0.30], facecolor=BG)
    axt = fig.add_axes([0.58, 0.04, 0.40, 0.42], facecolor=BG); axt.axis("off")
    fig.text(0.02, 0.94, "SKN-V1  swarm simulation", fontsize=17, fontweight="bold", color=FG)
    fig.text(0.02, 0.905, "computed live by skn — simulation only, no hardware", fontsize=9.5, color=DIM)
    errs = [f[2] for f in frames]
    steps = [f[0] for f in frames]
    trail = {i: [] for i in range(len(frames[0][1]))}

    def draw(k):
        fi = min(k, len(frames) - 1)
        step, P, err = frames[fi]
        ax3.cla(); ax3.set_facecolor(BG)
        for pane in (ax3.xaxis, ax3.yaxis, ax3.zaxis):
            pane.set_pane_color((0, 0, 0, 0)); pane.label.set_color(DIM)
            pane._axinfo["grid"].update(color="#1c2632", linewidth=0.6)
        ax3.tick_params(colors=DIM, labelsize=7)
        lim = 110 if step < 30 else max(40, np.abs(P).max() * 1.3)
        ax3.set_xlim(-lim, lim); ax3.set_ylim(-lim, lim); ax3.set_zlim(-lim, lim)
        for i, p in enumerate(P):
            if k < len(frames):
                trail[i].append(p.copy())
            T = np.array(trail[i])
            ax3.plot(T[:, 0], T[:, 1], T[:, 2], color=BLUE, alpha=0.35, lw=1)
        D = np.linalg.norm(P[:, None] - P[None], axis=-1)
        for i in range(len(P)):
            for j in range(i + 1, len(P)):
                if D[i, j] < comm_r:
                    ax3.plot(*zip(P[i], P[j]), color=GREEN, lw=1.4, alpha=0.9)
        ax3.scatter(P[:, 0], P[:, 1], P[:, 2], s=46, color=ORANGE, depthshade=False, edgecolors=FG, linewidths=0.6)
        ax3.view_init(elev=28, azim=35 + 0.6 * k)

        axe.cla(); axe.set_facecolor(BG)
        axe.semilogy(steps[: fi + 1], errs[: fi + 1], color=BLUE, lw=2)
        axe.set_xlim(0, steps[-1]); axe.set_ylim(min(errs) * 0.5, max(errs) * 2)
        axe.set_title("formation error (m), log scale", color=FG, fontsize=10, loc="left")
        axe.set_xlabel("step", fontsize=8); axe.tick_params(labelsize=7)
        for s in axe.spines.values():
            s.set_color("#243244")

        axt.cla(); axt.axis("off")
        b0, b1 = betti(P, comm_r)
        old = graph_cycle_rank(P, comm_r)
        if k < len(frames) + hold_form:
            lines = [(f"step {step:>3}   error {err:10.6f} m", FG, 12),
                     (f"topology guard at r = {comm_r:.0f} m:", DIM, 10),
                     (f"  pieces  b0 = {b0}    holes  b1 = {b1}", GREEN if b0 == 1 else RED, 12),
                     (f"  old graph count (removed): {old}", DIM, 10)]
            if fi == len(frames) - 1:
                lines.append(("ring closed: one piece, one real hole", ORANGE, 11))
        else:
            lines = [("signed docking (ML-DSA-65)", ORANGE, 12)] + [
                (s, RED if "REFUSED" in s else (GREEN if "VALID" in s else FG), 10) for s in story]
        y = 0.95
        for text, color, size in lines:
            axt.text(0.0, y, text, color=color, fontsize=size, family="DejaVu Sans Mono", va="top", transform=axt.transAxes)
            y -= 0.11 if size > 10.5 else 0.088
        return []

    anim = FuncAnimation(fig, draw, frames=total, interval=1000 / a.fps, blit=False)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    anim.save(a.out + ".gif", writer=PillowWriter(fps=a.fps))
    print(f"wrote {a.out}.gif  ({total} frames, final formation error {res['final_error_m']:.6f} m)")
    if shutil.which("ffmpeg"):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.out + ".gif", "-movflags", "faststart",
                        "-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", a.out + ".mp4"], check=False)
        if os.path.exists(a.out + ".mp4"):
            print(f"wrote {a.out}.mp4")
    for s in story:
        print("  " + s)
    for r in reasons:
        print("  reason: " + r)


if __name__ == "__main__":
    main()
