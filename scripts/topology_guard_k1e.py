"""K1e (docs/PREREG_2026-09-27.md): how often does the topology guard fire in skn.rendezvous, and how many
communication links does its reconfiguration protocol cut? Run with the guard the code has at the time."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import skn.swarm as sw
from skn.simulation import rendezvous

cut = {"links": 0}
orig = sw.SwarmGossipProtocol._formation_reconfiguration_protocol


def counted(self):
    before = sum(len(v) for v in self.topology.values())
    orig(self)
    cut["links"] += before - sum(len(v) for v in self.topology.values())


sw.SwarmGossipProtocol._formation_reconfiguration_protocol = counted
res = rendezvous(n_nodes=6, verbose=False)
frp = res["frp_events"]
print("guard:", (sw.SwarmGossipProtocol.compute_betti_one.__doc__ or "E - V + C (graph cycle rank)").splitlines()[0])
print(f"reconfiguration protocol calls: {frp}  directed links cut: {cut['links']}")
