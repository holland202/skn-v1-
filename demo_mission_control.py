import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch
from matplotlib.collections import LineCollection
import matplotlib.patheffects as path_effects
import os
import time

# Create output dir
os.makedirs("demo_frames", exist_ok=True)

# Tetrahedron formation targets
scale = 80
targets = np.array([
    [1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]
], dtype=np.float32) * scale

# Node colors (sci-fi palette)
colors = ["#00ffc8", "#00aaff", "#ff6b35", "#ff00aa"]
names = ["SKN-000", "SKN-001", "SKN-002", "SKN-003"]

# Initialize nodes with random positions
np.random.seed(42)
nodes = np.random.uniform(-150, 150, (4, 3)).astype(np.float32)
velocities = np.zeros((4, 3), dtype=np.float32)

# Simulation params
dt = 0.05
n_steps = 300
spring_k = 0.05
damping = 0.92
target_spring_k = 0.008

# Vault tracking
vault = [0, 0, 0, 0]
vault_total = 0

# Betti-1 tracking
killed = None
betti1 = 0

# Mode
mode = "formation"  # or "rendezvous"

print("=" * 60)
print("  SKN-V1 MISSION CONTROL // SOVEREIGN KINEMATIC NODE")
print("=" * 60)
print()
print("  Generating", n_steps, "frames...")
print()


for step in range(n_steps):
    alive_mask = np.ones(4, dtype=bool)
    if killed is not None:
        alive_mask[killed] = False
    
    alive_idx = np.where(alive_mask)[0]
    n_alive = len(alive_idx)
    
    # Centroid
    centroid = nodes[alive_mask].mean(axis=0) if n_alive > 0 else np.zeros(3)
    
    # Target forces
    if mode == "formation":
        for i, idx in enumerate(alive_idx):
            target = targets[i % len(targets)]
            diff = target - nodes[idx]
            velocities[idx] += diff * target_spring_k
    else:
        for idx in alive_idx:
            diff = -nodes[idx]
            velocities[idx] += diff * target_spring_k * 0.75
    
    # Spring forces between neighbors
    for i in range(n_alive):
        for j in range(i + 1, n_alive):
            ni, nj = alive_idx[i], alive_idx[j]
            diff = nodes[ni] - nodes[nj]
            dist = np.linalg.norm(diff) + 1e-6
            target_dist = 110.0 if mode == "formation" else 0.0
            force = (dist - target_dist) * spring_k * 0.002
            f = (diff / dist) * force
            velocities[ni] -= f
            velocities[nj] += f
    
    # Damping
    velocities *= damping
    nodes += velocities
    
    # Vault commits
    for idx in alive_idx:
        if np.random.random() < 0.3:
            vault[idx] += 1
            vault_total += 1
    
    # Decay spring constant
    spring_k *= 0.9995
    
    # Compute metrics
    form_err = 0.0
    if mode == "formation" and n_alive > 0:
        for i, idx in enumerate(alive_idx):
            target = targets[i % len(targets)]
            form_err += np.linalg.norm(nodes[idx] - target)
        form_err /= n_alive
    
    cent_err = np.linalg.norm(centroid)
    fisher_norm = 2.5 + 0.3 * np.sin(step * 0.05)
    
    # Render frame every 5 steps
    if step % 5 == 0 or step == n_steps - 1:
        fig = plt.figure(figsize=(14, 10), facecolor="#050508")
        ax = fig.add_subplot(111, projection="3d")
        ax.set_facecolor("#050508")
        
        # Grid styling
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        ax.xaxis.pane.set_edgecolor((0, 0.2, 0.15, 0.3))
        ax.yaxis.pane.set_edgecolor((0, 0.2, 0.15, 0.3))
        ax.zaxis.pane.set_edgecolor((0, 0.2, 0.15, 0.3))
        ax.tick_params(colors="#00ffc8", labelsize=8)
        ax.set_title("SKN-V1 // FORMATION VIEW: TETRAHEDRON 20M", 
                     color="#00ffc8", fontsize=12, fontweight="bold", pad=20)
        
        # Draw connections
        for i in range(n_alive):
            for j in range(i + 1, n_alive):
                ni, nj = alive_idx[i], alive_idx[j]
                xs = [nodes[ni, 0], nodes[nj, 0]]
                ys = [nodes[ni, 1], nodes[nj, 1]]
                zs = [nodes[ni, 2], nodes[nj, 2]]
                ax.plot(xs, ys, zs, color="#00ffc8", alpha=0.3, linewidth=1)
        
        # Draw target markers
        if mode == "formation":
            for t in targets:
                ax.scatter(*t, color="#00ffc8", s=30, alpha=0.4, marker="o")
        
        # Draw nodes
        for i, idx in enumerate(alive_idx):
            pos = nodes[idx]
            color = colors[idx]
            # Glow effect via multiple scatter sizes
            ax.scatter(*pos, color=color, s=400, alpha=0.15)
            ax.scatter(*pos, color=color, s=150, alpha=0.4)
            ax.scatter(*pos, color=color, s=60, alpha=1.0, edgecolors="white", linewidths=1)
            # Label
            ax.text(pos[0], pos[1], pos[2] + 25, names[idx], 
                   color=color, fontsize=9, fontweight="bold")
        
        # Set limits
        ax.set_xlim(-150, 150)
        ax.set_ylim(-150, 150)
        ax.set_zlim(-150, 150)
        
        # Add telemetry overlay as text
        telemetry = (
            f"MESH: {n_alive}/4  |  β₁: {betti1}  |  VAULT: {vault_total}\\n"
            f"CENTROID ERR: {cent_err/10:.4f} m  |  FORM ERR: {form_err/10:.4f} m\\n"
            f"FISHER NORM: {fisher_norm:.2f}  |  STEP: {step}/{n_steps}"
        )
        fig.text(0.02, 0.02, telemetry, color="#00ffc8", fontsize=10,
                fontfamily="monospace", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#0a0a0f", 
                         edgecolor="#00ffc8", alpha=0.8))
        
        # Save frame
        plt.savefig(f"demo_frames/frame_{step:04d}.png", dpi=120, 
                   facecolor="#050508", bbox_inches="tight")
        plt.close()
        
        # Terminal progress
        bar_len = 30
        filled = int(bar_len * (step + 1) / n_steps)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"\\r  [{bar}] {step+1}/{n_steps}  form_err={form_err/10:.4f}m", end="", flush=True)

print()
print()
print("=" * 60)
print("  FRAMES GENERATED: demo_frames/")
print("=" * 60)

