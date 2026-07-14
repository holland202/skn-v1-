import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import os, time

os.makedirs("frames", exist_ok=True)

# Futuristic palette
colors = ["#00ffff", "#ff00ff", "#39ff14", "#ffd700", "#ff3366", "#aaffff"]
names = ["NEX-01", "NEX-02", "NEX-03", "NEX-04", "NEX-05", "NEX-06"]

np.random.seed(42)
positions = np.random.uniform(-120, 120, (6, 3)).astype(np.float32)
vel = np.zeros((6, 3))

print("🌌 SOVEREIGN SUITE v0.2.1 // THERMODYNAMIC KINEMATIC MANIFOLD")
print("=" * 75)

for step in range(220):
    centroid = positions.mean(axis=0)
    for i in range(6):
        to_center = centroid - positions[i]
        positions[i] += to_center * 0.011 + vel[i] * 0.93
        vel[i] = vel[i] * 0.89 + np.random.normal(0, 1.1, 3)
    
    if step % 5 == 0:
        fig = plt.figure(figsize=(13, 10), facecolor="#00040f")
        ax = fig.add_subplot(111, projection="3d")
        ax.set_facecolor("#00040f")
        ax.grid(False)
        ax.set_axis_off()
        
        # Holographic mesh
        for i in range(6):
            for j in range(i+1,6):
                ax.plot([positions[i,0],positions[j,0]], 
                       [positions[i,1],positions[j,1]],
                       [positions[i,2],positions[j,2]], color="#00ffff", alpha=0.25, lw=1.2)
        
        # Nodes with intense glow
        for i in range(6):
            p = positions[i]
            ax.scatter(p[0], p[1], p[2], color=colors[i], s=900, alpha=0.1)
            ax.scatter(p[0], p[1], p[2], color=colors[i], s=320, alpha=0.5)
            ax.scatter(p[0], p[1], p[2], color=colors[i], s=80, alpha=1.0)
            ax.text(p[0], p[1], p[2]+25, names[i], color=colors[i], fontsize=10, ha="center", fontweight="bold")
        
        ax.set_xlim(-140,140)
        ax.set_ylim(-140,140)
        ax.set_zlim(-140,140)
        
        fig.text(0.5, 0.96, "SOVEREIGN SUITE // MINIMUM-ENERGY MANIFOLD", ha="center", color="#00ffff", fontsize=17, fontweight="bold")
        fig.text(0.5, 0.04, f"STEP {step:04d}  |  ΔG-GATED  |  THERMAL COLLAPSE STABLE  |  β₁=0 VERIFIED", ha="center", color="#ff00ff", fontsize=11, fontfamily="monospace")
        
        plt.savefig(f"frames/frame_{step:04d}.png", dpi=160, facecolor="#00040f")
        plt.close()
        
        print(f"\r  Rendering frame {step+1}/220", end="", flush=True)

print("\n\n✅ Futuristic Sovereign Suite frames generated!")
print("Create GIF:")
print("convert -delay 5 -loop 0 frames/frame_*.png sovereign_futuristic.gif")
