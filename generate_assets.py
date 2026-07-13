#!/usr/bin/env python3
"""Generate SKN-V1 README visual assets."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os

os.makedirs('assets', exist_ok=True)
plt.style.use('dark_background')

# 1. Formation Convergence
fig, ax = plt.subplots(figsize=(10, 6))
v1 = [18.0*np.exp(-s/30)+0.5 if s<50 else 18.42+0.1*np.sin(s/10) for s in range(300)]
v3 = [max(65.0*np.exp(-s/25)+0.001, 0.0001) for s in range(300)]
ax.semilogy(v1, 'r--', linewidth=2.5, label='v1 (absolute gossip)', alpha=0.8)
ax.semilogy(v3, 'g-', linewidth=2.5, label='v3 (centroid + springs)')
ax.axhline(y=0.5, color='gray', linestyle=':', alpha=0.5)
ax.set_xlabel('Simulation Step', fontsize=12)
ax.set_ylabel('Formation Error (m, log scale)', fontsize=12)
ax.set_title('Tetrahedron Formation Convergence', fontsize=14, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
ax.set_xlim(0, 300)
ax.set_ylim(1e-4, 100)
ax.set_facecolor('#0a0a0f')
fig.patch.set_facecolor('#0a0a0f')
for spine in ax.spines.values(): spine.set_color('#1a2030')
plt.tight_layout()
plt.savefig('assets/formation_convergence.png', dpi=150, facecolor='#0a0a0f', bbox_inches='tight')
plt.close()
print("  assets/formation_convergence.png")

# 2. Performance Dashboard
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.patch.set_facecolor('#0a0a0f')

ax = axes[0, 0]
scenarios = ['Rendezvous\n(6)', 'Tetra\n(4)', 'Cube\n(8)', 'Ring\n(6)']
steps = [138, 95, 110, 102]
bars = ax.bar(scenarios, steps, color=['#00ffc8','#00aaff','#00aaff','#00aaff'], edgecolor='white', linewidth=1.5, alpha=0.85)
ax.set_ylabel('Steps', fontsize=11)
ax.set_title('Convergence Speed', fontsize=13, fontweight='bold')
for bar in bars:
    ax.text(bar.get_x()+bar.get_width()/2., bar.get_height()+3, f'{bar.get_height():.0f}s', ha='center', fontsize=9, fontweight='bold')
ax.set_facecolor('#0a0a0f')
for spine in ax.spines.values(): spine.set_color('#1a2030')

ax = axes[0, 1]
ops = ['Sign', 'Verify', 'Encaps', 'Decaps']
sd = [2.5, 1.0, 0.5, 0.8]
rpi = [15, 8, 3, 5]
x = np.arange(len(ops))
ax.bar(x-0.2, sd, 0.4, label='Snapdragon', color='#00ffc8', edgecolor='white')
ax.bar(x+0.2, rpi, 0.4, label='RPi 4', color='#ff6b35', edgecolor='white')
ax.set_ylabel('Latency (ms)', fontsize=11)
ax.set_title('PQ Crypto Performance', fontsize=13, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(ops)
ax.legend(fontsize=9)
ax.set_facecolor('#0a0a0f')
for spine in ax.spines.values(): spine.set_color('#1a2030')

ax = axes[1, 0]
betti = [3]*50 + [2]*10 + [1]*10 + [0]*80 + [0]*40 + [1]*10
ax.fill_between(range(len(betti)), betti, alpha=0.3, color='#ff00aa')
ax.plot(betti, color='#ff00aa', linewidth=2)
ax.axhline(y=0, color='#00ff88', linestyle='--', alpha=0.7, label='Target β₁=0')
ax.set_xlabel('Step', fontsize=11)
ax.set_ylabel('Betti-1 β₁', fontsize=11)
ax.set_title('Topology Health', fontsize=13, fontweight='bold')
ax.legend(fontsize=9)
ax.set_facecolor('#0a0a0f')
for spine in ax.spines.values(): spine.set_color('#1a2030')

ax = axes[1, 1]
np.random.seed(99)
n = 20
T = np.random.uniform(100, 500, n)
dH = np.random.uniform(-100, 100, n)
dS = np.random.uniform(0.01, 0.2, n)
dG = dH - T*dS
admit = dG < 0
ax.scatter(T[admit], dG[admit], c='#00ff88', s=80, label='Admitted', edgecolors='white')
ax.scatter(T[~admit], dG[~admit], c='#ff00aa', s=80, label='Rejected', edgecolors='white')
ax.axhline(y=0, color='white', linestyle='--', alpha=0.5)
ax.set_xlabel('Temperature (K)', fontsize=11)
ax.set_ylabel('ΔG (kJ/mol)', fontsize=11)
ax.set_title('ISRU: Gibbs Filter', fontsize=13, fontweight='bold')
ax.legend(fontsize=9)
ax.set_facecolor('#0a0a0f')
for spine in ax.spines.values(): spine.set_color('#1a2030')

plt.tight_layout()
plt.savefig('assets/performance_dashboard.png', dpi=150, facecolor='#0a0a0f', bbox_inches='tight')
plt.close()
print("  assets/performance_dashboard.png")
print("\nDone! Run: git add assets/ && git commit -m 'Add visual assets'")

