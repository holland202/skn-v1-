import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from skn.simulation import formation, _get_formation_targets
from skn.simulation_v3 import formation_v3
from skn.node import SKNV1_SovereignNode

BG, FG, MUTED, GRID = "#0d1117", "#c9d1d9", "#8b949e", "#30363d"

def gradient_only(n_nodes=4, shape="tetrahedron", scale=20.0, n_steps=500, dt=0.05):
    """formation_v3's loop with both hand-written correctors removed."""
    targets = _get_formation_targets(n_nodes, shape, scale)
    rng = np.random.default_rng(seed=7)
    nodes = [SKNV1_SovereignNode("FRM-%03d" % i,
             initial_pose=rng.uniform(-100, 100, 6).astype(np.float32))
             for i in range(n_nodes)]
    errs = []
    for _ in range(n_steps):
        for i, node in enumerate(nodes):
            node.step(targets[i].copy(), dt)
        errs.append(float(np.mean([np.linalg.norm(nodes[i].pose[:3] - targets[i][:3])
                                   for i in range(n_nodes)])))
    return errs

print("running real simulations (no synthetic curves in this script)")
v3 = formation_v3(verbose=False)["formation_errors"]
fm = formation(verbose=False)["formation_errors"]
go = gradient_only()
print("  formation_v3()   %3d steps  %9.3f m -> %9.6f m" % (len(v3), v3[0], v3[-1]))
print("  formation()      %3d steps  %9.3f m -> %9.6f m" % (len(fm), fm[0], fm[-1]))
print("  gradient only    %3d steps  %9.3f m -> %9.6f m" % (len(go), go[0], go[-1]))

fig, ax = plt.subplots(figsize=(12, 7))
ax.set_facecolor(BG); fig.patch.set_facecolor(BG)
ax.plot(range(len(v3)), v3, color="#58a6ff", linewidth=2.5,
        label="formation_v3: gradient + 2 correctors  (final %.6f m)" % v3[-1])
ax.plot(range(len(go)), go, color="#3fb950", linewidth=2.5,
        label="natural gradient alone  (final %.3f m)" % go[-1])
ax.plot(range(len(fm)), fm, color="#f0883e", linewidth=2.5,
        label="formation: gradient + gossip  (final %.3f m)" % fm[-1])
ax.set_yscale("symlog", linthresh=1e-3)
ax.set_xlabel("Simulation step", color=MUTED, fontsize=11)
ax.set_ylabel("Mean formation error (m)", color=MUTED, fontsize=11)
ax.set_title("Formation convergence - measured, not illustrated\nEvery point is returned by skn; run scripts/plot_formation_convergence.py to reproduce",
             color=FG, fontweight="bold", fontsize=13)
ax.legend(loc="upper right", facecolor="#161b22", edgecolor=GRID, labelcolor=FG, fontsize=10)
ax.grid(True, alpha=0.15, color=GRID, linestyle="-")
ax.tick_params(colors=MUTED)
for s in ax.spines.values(): s.set_color(GRID)
fig.text(0.012, 0.005, "Simulation only. No hardware. The two correctors in formation_v3 are decaying-gain proportional terms written directly into pose; they close the last fraction of a metre, the gradient does the rest.",
         color=MUTED, fontsize=8.5, va="bottom")
plt.tight_layout()
plt.savefig("assets/formation_convergence_dark.png", dpi=200, bbox_inches="tight", facecolor=BG, edgecolor="none")
plt.close()
print("wrote assets/formation_convergence_dark.png")
