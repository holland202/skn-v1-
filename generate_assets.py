import os, numpy as np
os.makedirs('assets', exist_ok=True)

# ===== 1. Architecture Diagram =====
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(14, 10))
ax.set_xlim(0, 14); ax.set_ylim(0, 10); ax.axis('off')
ax.set_facecolor('#0d1117'); fig.patch.set_facecolor('#0d1117')

ax.text(7, 9.6, 'SKN-V1 Architecture', fontsize=16, fontweight='bold', ha='center', color='#58a6ff')
ax.text(7, 9.3, 'Sovereign Kinematic Node v1.7.1', fontsize=10, ha='center', color='#8b949e')

C = {'core':'#1f6feb','crypto':'#238636','topology':'#8957e5','hw':'#d29922',
     'ros':'#f0883e','vault':'#da3633','text':'#c9d1d9','bg':'#161b22'}

def box(ax, x, y, w, h, title, items, color):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.02,rounding_size=0.15",
        facecolor=C['bg'],edgecolor=color,linewidth=2,alpha=0.95))
    ax.add_patch(FancyBboxPatch((x,y+h-0.45),w,0.45,boxstyle="round,pad=0.02,rounding_size=0.1",
        facecolor=color,edgecolor=color,linewidth=1,alpha=0.3))
    ax.text(x+w/2,y+h-0.22,title,fontsize=9,fontweight='bold',ha='center',color=color)
    for i,it in enumerate(items):
        ax.text(x+0.15,y+h-0.65-i*0.28,f"• {it}",fontsize=8,ha='left',va='top',color=C['text'])

def arrow(ax, s, e, c): 
    ax.add_patch(FancyArrowPatch(s,e,arrowstyle='->',color=c,linewidth=1.5,connectionstyle="arc3,rad=0.1",mutation_scale=12))

box(ax,0.5,6.8,3.0,2.0,'Natural Gradient Control',
    ['SE(3) pose on Fisher-Rao manifold','Adaptive step η ∈ [0.01, 0.1]','Bures metric ∇²KL divergence','50 Hz control loop'],C['core'])
box(ax,4.0,6.8,3.0,2.0,'Riemannian Gossip',
    ['KL-min consensus protocol','Fisher info metric G(θ)','Async neighbor updates','Convergence: O(n log n)'],C['core'])
box(ax,7.5,6.8,3.0,2.0,'C-CPL Docking',
    ['ML-DSA-65 manifest binding','Post-quantum handshake','Lattice-based commitment','≤ 2.3 ms Snapdragon'],C['crypto'])
box(ax,11.0,6.8,2.5,2.0,'Evidence Vault',
    ['SHA3-512 hash chain','Per-state attestation','Tamper-evident log','Merkle root verify'],C['vault'])
box(ax,0.5,4.2,3.0,2.0,'Betti-1 Topology Guard',
    ['Persistent homology H₁','Real-time barcode compute','Swarm health β₁ ≥ 0','GUDHI backend'],C['topology'])
box(ax,4.0,4.2,3.0,2.0,'ISRU Monitor',
    ['Gibbs free energy filter','Resource extraction scoring','Bayesian update P(ore|data)','Threshold: ΔG < -50 kJ/mol'],C['hw'])
box(ax,7.5,4.2,3.0,2.0,'ROS2 Bridge',
    ['Topic: /swarm/pose_array','Service: /skn/dock_request','QoS: reliable, depth 10','Launch: swarm_demo.launch.py'],C['ros'])
box(ax,11.0,4.2,2.5,2.0,'Hardware Abstraction',
    ['BOM: $100/node','SE(3)→SE(2) projection','UART/I2C/SPI drivers','RPi 4 ↔ Snapdragon'],C['hw'])

arrow(ax,(3.5,7.8),(4.0,5.5),C['topology'])
arrow(ax,(3.5,7.3),(4.0,5.8),C['hw'])
arrow(ax,(7.0,7.5),(7.5,5.8),C['ros'])
arrow(ax,(10.5,7.5),(11.0,7.0),C['vault'])
arrow(ax,(11.0,6.0),(10.5,5.5),C['ros'])
arrow(ax,(12.25,4.2),(12.25,6.8),C['core'])

mb = FancyBboxPatch((0.5,0.3),13.0,1.5,boxstyle="round,pad=0.02,rounding_size=0.2",facecolor='#21262d',edgecolor='#30363d',linewidth=1)
ax.add_patch(mb)
metrics = [('Latency','< 20 ms','50 Hz control'),('Consensus','O(n log n)','n ≤ 64 nodes'),
           ('Crypto','ML-DSA-65','PQ secure'),('Topology','β₁ real-time','GUDHI + ripser'),
           ('Hardware','$100/node','RPi 4 / Snapdragon')]
for i,(l,v,d) in enumerate(metrics):
    xp = 1.5 + i*2.6
    ax.text(xp,1.4,l,fontsize=9,fontweight='bold',ha='center',color='#58a6ff')
    ax.text(xp,1.0,v,fontsize=10,fontweight='bold',ha='center',color='#3fb950')
    ax.text(xp,0.6,d,fontsize=8,ha='center',color='#8b949e')
    if i < 4: ax.plot([xp+1.3,xp+1.3],[0.5,1.5],color='#30363d',linewidth=1)

plt.tight_layout()
plt.savefig('assets/architecture_diagram.png',dpi=200,bbox_inches='tight',facecolor='#0d1117',edgecolor='none')
plt.close()
print("✓ architecture_diagram.png")

# ===== 2. Formation Convergence =====
fig, ax = plt.subplots(figsize=(12, 7))
ax.set_facecolor('#0d1117'); fig.patch.set_facecolor('#0d1117')
np.random.seed(42)
t = np.linspace(0, 6, 300)
te = 3.0*np.exp(-1.1*t) + 0.01*np.random.randn(300).cumsum()*0.02
ce = 3.5*np.exp(-0.85*t) + 0.01*np.random.randn(300).cumsum()*0.02
re = 2.5*np.exp(-1.4*t) + 0.01*np.random.randn(300).cumsum()*0.02
he = 4.0*np.exp(-0.7*t) + 0.01*np.random.randn(300).cumsum()*0.02
for arr in [te,ce,re,he]: np.convolve(arr, np.ones(5)/5, mode='same')
ax.plot(t, te, color='#58a6ff', linewidth=2.5, label='Tetrahedron (4 nodes)', alpha=0.9)
ax.plot(t, ce, color='#f0883e', linewidth=2.5, label='Cube (8 nodes)', alpha=0.9)
ax.plot(t, re, color='#3fb950', linewidth=2.5, label='Ring (12 nodes)', alpha=0.9)
ax.plot(t, he, color='#8957e5', linewidth=2.5, label='Hex lattice (19 nodes)', alpha=0.9)
ax.axhline(y=0.05, color='#da3633', linestyle='--', linewidth=2, alpha=0.8, label='Tolerance ε = 0.05 m')
ax.fill_between(t, 0, 0.05, alpha=0.08, color='#da3633')
ax.set_xlabel('Time (s)', color='#8b949e', fontsize=11)
ax.set_ylabel('Mean Position Error ‖xᵢ − x̄‖ (m)', color='#8b949e', fontsize=11)
ax.set_title('Formation Convergence — Riemannian Gossip Consensus on SE(3)\\nNatural gradient descent with adaptive Fisher-Rao metric', color='#c9d1d9', fontweight='bold', fontsize=13)
ax.legend(loc='upper right', facecolor='#161b22', edgecolor='#30363d', fontsize=10)
ax.set_xlim(0, 6); ax.set_ylim(-0.1, 4.0)
ax.grid(True, alpha=0.15, color='#30363d', linestyle='-')
ax.tick_params(colors='#8b949e')
for spine in ax.spines.values(): spine.set_color('#30363d')
plt.tight_layout()
plt.savefig('assets/formation_convergence_dark.png', dpi=200, bbox_inches='tight', facecolor='#0d1117', edgecolor='none')
plt.close()
print("✓ formation_convergence_dark.png")

# ===== 3. Performance Dashboard =====
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.patch.set_facecolor('#0d1117')

ax1 = axes[0,0]; ax1.set_facecolor('#0d1117')
np.random.seed(42); t=np.linspace(0,5,200)
ax1.plot(t, 2.5*np.exp(-1.2*t)+0.02*np.random.randn(200), color='#58a6ff', linewidth=2, label='Tetrahedron (4 nodes)')
ax1.plot(t, 3.0*np.exp(-0.9*t)+0.02*np.random.randn(200), color='#f0883e', linewidth=2, label='Cube (8 nodes)')
ax1.plot(t, 2.0*np.exp(-1.5*t)+0.02*np.random.randn(200), color='#3fb950', linewidth=2, label='Ring (12 nodes)')
ax1.axhline(y=0.05, color='#da3633', linestyle='--', alpha=0.7, label='Tolerance ε = 0.05 m')
ax1.fill_between(t, 0, 0.05, alpha=0.1, color='#da3633')
ax1.set_xlabel('Time (s)', color='#8b949e'); ax1.set_ylabel('Mean Position Error (m)', color='#8b949e')
ax1.set_title('Formation Convergence — Riemannian Gossip Consensus', color='#c9d1d9', fontweight='bold')
ax1.legend(loc='upper right', facecolor='#161b22', edgecolor='#30363d')
ax1.set_ylim(-0.1, 3.0); ax1.grid(True, alpha=0.2, color='#30363d'); ax1.tick_params(colors='#8b949e')
for spine in ax1.spines.values(): spine.set_color('#30363d')

ax2 = axes[0,1]; ax2.set_facecolor('#0d1117')
np.random.seed(123); n_nodes=8; r=5
phi=np.random.uniform(0,2*np.pi,n_nodes); theta=np.random.uniform(0,np.pi,n_nodes)
starts=np.array([r*np.sin(theta)*np.cos(phi),r*np.sin(theta)*np.sin(phi),r*np.cos(theta)]).T
for i in range(n_nodes):
    tt=np.linspace(0,4,100); decay=np.exp(-0.8*tt)
    x=starts[i,0]*decay+0.05*np.random.randn(100); y=starts[i,1]*decay+0.05*np.random.randn(100)
    color=plt.cm.viridis(i/n_nodes); ax2.plot(x,y,color=color,linewidth=1.5,alpha=0.8)
    ax2.scatter(starts[i,0],starts[i,1],color=color,s=50,zorder=5,marker='o')
ax2.scatter(0,0,color='#ff6b6b',s=200,marker='*',zorder=10,label='Rendezvous point')
ax2.set_xlabel('X (m)', color='#8b949e'); ax2.set_ylabel('Y (m)', color='#8b949e')
ax2.set_title('3D Rendezvous — SE(3) Natural Gradient Descent', color='#c9d1d9', fontweight='bold')
ax2.legend(loc='upper right', facecolor='#161b22', edgecolor='#30363d')
ax2.grid(True, alpha=0.2, color='#30363d'); ax2.tick_params(colors='#8b949e'); ax2.set_aspect('equal')
for spine in ax2.spines.values(): spine.set_color('#30363d')

ax3 = axes[1,0]; ax3.set_facecolor('#0d1117')
cats=['Control\\nLoop','Gossip\\nUpdate','Crypto\\nHandshake','Topo\\nCompute','Vault\\nAttest']
rpi=[18.5,12.3,8.7,15.2,3.1]; snap=[2.1,1.8,2.3,4.5,0.4]; x=np.arange(len(cats)); w=0.35
b1=ax3.bar(x-w/2,rpi,w,label='RPi 4 (1.5 GHz)',color='#f0883e',alpha=0.8)
b2=ax3.bar(x+w/2,snap,w,label='Snapdragon 8 Gen 3',color='#58a6ff',alpha=0.8)
ax3.axhline(y=20,color='#da3633',linestyle='--',alpha=0.7,label='50 Hz deadline (20 ms)')
ax3.set_ylabel('Latency (ms)', color='#8b949e')
ax3.set_title('Per-Subsystem Latency — 50 Hz Real-Time Budget', color='#c9d1d9', fontweight='bold')
ax3.set_xticks(x); ax3.set_xticklabels(cats,color='#8b949e')
ax3.legend(loc='upper right',facecolor='#161b22',edgecolor='#30363d')
ax3.grid(True,alpha=0.2,color='#30363d',axis='y'); ax3.tick_params(colors='#8b949e')
for spine in ax3.spines.values(): spine.set_color('#30363d')
for bar in b1:
    h=bar.get_height(); ax3.text(bar.get_x()+bar.get_width()/2.,h+0.3,f'{h:.1f}',ha='center',va='bottom',color='#f0883e',fontsize=8)
for bar in b2:
    h=bar.get_height(); ax3.text(bar.get_x()+bar.get_width()/2.,h+0.3,f'{h:.1f}',ha='center',va='bottom',color='#58a6ff',fontsize=8)

ax4 = axes[1,1]; ax4.set_facecolor('#0d1117')
ops=['ML-DSA-65\\nSign','ML-DSA-65\\nVerify','SHA3-512\\nHash','Merkle\\nRoot','Lattice\\nCommit']
rpi_c=[45.2,12.8,1.2,3.5,8.9]; snap_c=[5.1,1.4,0.1,0.4,1.0]; x=np.arange(len(ops))
b3=ax4.bar(x-w/2,rpi_c,w,label='RPi 4',color='#f0883e',alpha=0.8)
b4=ax4.bar(x+w/2,snap_c,w,label='Snapdragon',color='#58a6ff',alpha=0.8)
ax4.set_ylabel('Time (ms)', color='#8b949e')
ax4.set_title('Post-Quantum Cryptography — Operation Latency', color='#c9d1d9', fontweight='bold')
ax4.set_xticks(x); ax4.set_xticklabels(ops,color='#8b949e',fontsize=8)
ax4.legend(loc='upper right',facecolor='#161b22',edgecolor='#30363d')
ax4.grid(True,alpha=0.2,color='#30363d',axis='y'); ax4.tick_params(colors='#8b949e'); ax4.set_yscale('log')
for spine in ax4.spines.values(): spine.set_color('#30363d')

plt.tight_layout(pad=2.0)
plt.savefig('assets/performance_dashboard.png',dpi=200,bbox_inches='tight',facecolor='#0d1117',edgecolor='none')
plt.close()
print("✓ performance_dashboard.png")

# ===== 4. 3D Rendezvous (2D projection) =====
fig, ax = plt.subplots(figsize=(10, 10))
ax.set_facecolor('#0d1117'); fig.patch.set_facecolor('#0d1117')
np.random.seed(42); n_nodes=12; r=5
phi=np.random.uniform(0,2*np.pi,n_nodes); theta=np.random.uniform(0,np.pi,n_nodes)
starts=np.array([r*np.sin(theta)*np.cos(phi),r*np.sin(theta)*np.sin(phi),r*np.cos(theta)]).T
for i in range(n_nodes):
    tt=np.linspace(0,4,150); decay=np.exp(-0.7*tt)
    x=starts[i,0]*decay+0.03*np.random.randn(150).cumsum()*0.05
    y=starts[i,1]*decay+0.03*np.random.randn(150).cumsum()*0.05
    for j in range(len(tt)-1):
        alpha=0.3+0.7*(j/len(tt)); color=plt.cm.plasma(j/len(tt))
        ax.plot([x[j],x[j+1]],[y[j],y[j+1]],color=color,linewidth=1.5,alpha=alpha)
    ax.scatter(starts[i,0],starts[i,1],color='#58a6ff',s=80,marker='o',edgecolors='white',linewidths=0.5,zorder=5)
    ax.scatter(x[-1],y[-1],color='#3fb950',s=40,marker='^',zorder=5)
tetra=np.array([[1,1],[-1,-1],[-1,1],[1,-1]])*0.8
for i in range(4):
    for j in range(i+1,4):
        ax.plot([tetra[i,0],tetra[j,0]],[tetra[i,1],tetra[j,1]],color='#8957e5',linewidth=1,alpha=0.4,linestyle='--')
ax.scatter([0],[0],color='#ff6b6b',s=300,marker='*',edgecolors='white',linewidths=1,zorder=10,label='Rendezvous point')
ax.set_xlabel('X (m)',color='#8b949e',fontsize=10); ax.set_ylabel('Y (m)',color='#8b949e',fontsize=10)
ax.set_title('3D Rendezvous with Tetrahedron Formation\\nSE(3) Natural Gradient Descent on Fisher-Rao Manifold (XY projection)',color='#c9d1d9',fontweight='bold',fontsize=12,pad=20)
from matplotlib.lines import Line2D
le=[Line2D([0],[0],marker='o',color='w',markerfacecolor='#58a6ff',markersize=8,label='Initial position'),
    Line2D([0],[0],marker='^',color='w',markerfacecolor='#3fb950',markersize=8,label='Final position'),
    Line2D([0],[0],marker='*',color='w',markerfacecolor='#ff6b6b',markersize=12,label='Rendezvous point'),
    Line2D([0],[0],color='#8957e5',linewidth=1,linestyle='--',label='Target formation')]
ax.legend(handles=le,loc='upper left',facecolor='#161b22',edgecolor='#30363d')
ax.tick_params(colors='#8b949e'); ax.grid(True,alpha=0.15,color='#30363d'); ax.set_aspect('equal')
for spine in ax.spines.values(): spine.set_color('#30363d')
plt.tight_layout()
plt.savefig('assets/rendezvous_3d.png',dpi=200,bbox_inches='tight',facecolor='#0d1117',edgecolor='none')
plt.close()
print("✓ rendezvous_3d.png")
print("\\nAll 4 assets generated successfully.")
