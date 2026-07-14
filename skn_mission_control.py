import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import os

os.makedirs("frames", exist_ok=True)

colors = ["#00ffff", "#ff00ff", "#39ff14", "#ffd700"]
names = ["NEXUS-01", "NEXUS-02", "NEXUS-03", "NEXUS-04"]

np.random.seed(42)
positions = np.random.uniform(-110, 110, (4, 3)).astype(np.float32)
vel = np.zeros((4, 3))

print("🌌 NEXUS PROTOCOL v1.0 // SOVEREIGN QUANTUM KINEMATIC GRID")
print("=" * 70)

for step in range(200):
    centroid = positions.mean(axis=0)
    for i in range(4):
        to_center = centroid - positions[i]
        positions[i] += to_center * 0.012 + vel[i] * 0.95
        vel[i] = vel[i] * 0.88 + np.random.normal(0, 1.2, 3)
    
    if step % 5 == 0:
        fig = plt.figure(figsize=(13, 10), facecolor="#00050f")
        ax = fig.add_subplot(111, projection="3d")
        ax.set_facecolor("#00050f")
        ax.grid(False)
        ax.set_axis_off()
        
        # Holographic connections
        for i in range(4):
            for j in range(i+1,4):
                ax.plot([positions[i,0],positions[j,0]], 
                       [positions[i,1],positions[j,1]],
                       [positions[i,2],positions[j,2]], color="#00ffff", alpha=0.35, lw=1.5)
        
        # Nodes with multi-layer glow
        for i in range(4):
            p = positions[i]
            ax.scatter(p[0], p[1], p[2], color=colors[i], s=800, alpha=0.12)
            ax.scatter(p[0], p[1], p[2], color=colors[i], s=280, alpha=0.45)
            ax.scatter(p[0], p[1], p[2], color=colors[i], s=80, alpha=1.0, edgecolors="#ffffff", linewidth=1.2)
            ax.text(p[0], p[1], p[2]+22, names[i], color=colors[i], fontsize=10, ha="center", fontweight="bold")
        
        ax.set_xlim(-130,130)
        ax.set_ylim(-130,130)
        ax.set_zlim(-130,130)
        
        fig.text(0.5, 0.96, "NEXUS QUANTUM KINEMATIC SWARM", ha="center", color="#00ffff", fontsize=18, fontweight="bold")
        fig.text(0.5, 0.04, f"FRAME {step:04d}  |  QUANTUM ENTANGLEMENT STABLE  |  VAULT SYNC 99.997%", ha="center", color="#ff00ff", fontsize=11, fontfamily="monospace")
        
        plt.savefig(f"frames/frame_{step:04d}.png", dpi=160, facecolor="#00050f")
        plt.close()
        
        print(f"\r  Rendering futuristic frame {step+1}/200", end="", flush=True)

print("\n\n✅ Futuristic frames generated!")
print("Now create GIF:")
print("convert -delay 5 -loop 0 frames/frame_*.png nexus_futuristic.gif")
