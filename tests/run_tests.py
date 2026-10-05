#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest, numpy as np
import logging
logging.disable(logging.CRITICAL)

class TestPropulsionAllocator(unittest.TestCase):
    def setUp(self):
        from skn.node import PropulsionAllocator
        self.alloc = PropulsionAllocator(num_hets=6)
    def test_output_shape(self):
        self.assertEqual(self.alloc.allocate(np.zeros(6, np.float32)).shape, (9,))
    def test_het_bounded(self):
        u = self.alloc.allocate(np.random.normal(0,10,6).astype(np.float32))
        self.assertTrue(np.all(u[:6] <= 1.0 + 1e-6))
    def test_cmg_bounded(self):
        u = self.alloc.allocate(np.random.normal(0,10,6).astype(np.float32))
        self.assertTrue(np.all(np.abs(u[-3:]) <= self.alloc.cmg_saturation + 1e-6))

class TestEvidenceVault(unittest.TestCase):
    def setUp(self):
        from skn.node import EvidenceVault
        self.vault = EvidenceVault()
    def test_commit_returns_bytes(self):
        h = self.vault.commit(np.zeros(6, np.float32))
        self.assertEqual(len(h), 64)
    def test_chain_grows(self):
        for i in range(10): self.vault.commit(np.array([float(i)]*6, np.float32))
        self.assertEqual(self.vault.chain_length, 10)
    def test_intact_chain_verifies(self):
        for i in range(10): self.vault.commit(np.random.randn(7).astype(np.float32), {"i": i})
        self.assertTrue(self.vault.verify_chain())
    def test_tampered_state_fails(self):
        # anti-vacuity: editing a committed state must break verification
        for i in range(10): self.vault.commit(np.random.randn(7).astype(np.float32), {"i": i})
        bad = bytearray(self.vault._records[5]["preimage"]); bad[0] ^= 0xFF
        self.vault._records[5]["preimage"] = bytes(bad)
        self.assertFalse(self.vault.verify_chain())
    def test_tampered_hash_fails(self):
        for i in range(10): self.vault.commit(np.random.randn(7).astype(np.float32), {"i": i})
        self.vault._records[7]["hash"] = b"\x11" * 64
        self.assertFalse(self.vault.verify_chain())
    def test_reordered_chain_fails(self):
        for i in range(10): self.vault.commit(np.random.randn(7).astype(np.float32), {"i": i})
        r = self.vault._records
        r[3], r[4] = r[4], r[3]
        self.assertFalse(self.vault.verify_chain())
    def test_window_past_256_verifies(self):
        # K4 (2026-10-05): an honest vault with more than 256 commits used to fail its own check
        for i in range(300): self.vault.commit(np.array([float(i)]*6, np.float32), {"i": i})
        self.assertEqual(self.vault.chain_length, 256)
        self.assertTrue(self.vault.verify_chain())
        self.vault._records[10]["hash"] = b"\x11" * 64
        self.assertFalse(self.vault.verify_chain())

class TestISRUMonitor(unittest.TestCase):
    def setUp(self):
        from skn.node import ISRUMonitor
        self.isru = ISRUMonitor()
    def test_spontaneous(self):
        a, dG = self.isru.ingest_regolith(0.5, 500.0, -100.0, 0.2)
        self.assertTrue(a and dG < 0)
    def test_nonspontaneous(self):
        a, dG = self.isru.ingest_regolith(0.5, 300.0, 50.0, -0.1)
        self.assertFalse(a)

class TestSKNV1Node(unittest.TestCase):
    def setUp(self):
        from skn.node import SKNV1_SovereignNode
        self.node = SKNV1_SovereignNode("TEST")
    def test_step_moves_toward_target(self):
        t = np.array([10.,0.,0.,0.,0.,0.], np.float32)
        d0 = np.linalg.norm(self.node.pose[:3] - t[:3])
        for _ in range(20): self.node.step(t, 0.05)
        self.assertLess(np.linalg.norm(self.node.pose[:3] - t[:3]), d0)
    def test_convergence(self):
        t = np.array([1.,0.,0.,0.,0.,0.], np.float32)
        for _ in range(200): self.node.step(t, 0.05)
        self.assertLess(np.linalg.norm(self.node.pose[:3] - t[:3]), 0.5)

class TestFormationV3(unittest.TestCase):
    def test_tetra(self):
        from skn.simulation_v3 import formation_v3
        r = formation_v3(4, "tetrahedron", 20.0, 300, 0.05, False)
        self.assertLess(r["final_error_m"], 0.01)
    def test_cube(self):
        from skn.simulation_v3 import formation_v3
        r = formation_v3(8, "cube", 15.0, 300, 0.05, False)
        self.assertLess(r["final_error_m"], 0.01)

class TestTopologyGuard(unittest.TestCase):
    """K1, docs/PREREG_2026-09-27.md."""
    def ring(self, n=6):
        a = np.arange(n) * 2 * np.pi / n
        R = 1 / (2 * np.sin(np.pi / n))  # unit spacing between neighbours
        return np.c_[R * np.cos(a), R * np.sin(a), np.zeros(n)]
    def test_k1a_ring_has_one_hole_until_filled(self):
        from skn.topology import betti
        self.assertEqual(betti(self.ring(), 1.1), (1, 1))
        self.assertEqual(betti(self.ring(), 2.0)[1], 0)
    def test_k1b_filled_tetrahedron_is_not_a_hole(self):
        from skn.topology import betti, graph_cycle_rank
        P = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], float)
        self.assertEqual(betti(P, 2.0), (1, 0))
        self.assertEqual(graph_cycle_rank(P, 2.0), 3)
    def test_k1c_two_clusters(self):
        from skn.topology import betti
        P = np.array([[0, 0, 0], [0.5, 0, 0], [0, 0.5, 0], [10, 0, 0], [10.5, 0, 0], [10, 0.5, 0]], float)
        self.assertEqual(betti(P, 1.0)[0], 2)
    def test_k1d_matches_reference_on_random_clouds(self):
        from skn.topology import betti, rips_complex
        def rank2(rows):
            rows, r = [int("".join(map(str, row)) or "0", 2) for row in rows], 0
            basis = []
            for v in rows:
                for b in basis:
                    v = min(v, v ^ b)
                if v:
                    basis.append(v); r += 1
            return r
        rng = np.random.default_rng(7)
        for _ in range(200):
            n = int(rng.integers(2, 13)); P = rng.uniform(0, 3, (n, 2)); r = float(rng.uniform(0.5, 2.5))
            n_, E, T = rips_complex(P, r)
            d1 = [[1 if v in e else 0 for e in E] for v in range(n)]
            d2 = [[1 if set(e) <= set(t) else 0 for t in T] for e in E]
            r1 = rank2(d1) if E else 0; r2 = rank2(d2) if T else 0
            self.assertEqual(betti(P, r), (n - r1, len(E) - r1 - r2))
    def test_k1e_guard_does_not_cut_links_in_rendezvous(self):
        from skn.simulation import rendezvous
        self.assertEqual(rendezvous(n_nodes=6, n_steps=30, verbose=False)["frp_events"], 0)

class TestSignedDocking(unittest.TestCase):
    """K2, docs/PREREG_2026-09-27.md."""
    def setUp(self):
        from skn import ccpl
        if not ccpl.available():
            self.skipTest("dilithium-py not installed")
    def dock(self, nid="SKN-001"):
        from skn.node import SKNV1_SovereignNode
        n = SKNV1_SovereignNode(nid, np.zeros(6, np.float32))
        ok, detail = n.ccpl_initiate_dock("SKN-002", np.eye(3, dtype=np.float32), np.full(3, 0.2, np.float32))
        self.assertTrue(ok, detail)
        return n
    def test_k2a_genuine_record_verifies(self):
        from skn.ccpl import verify_dock
        n = self.dock()
        self.assertEqual(verify_dock(n.last_dock_record, n.dock_public_key), (True, "ML-DSA-65 signature valid"))
        last = n.vault._records[-1]["preimage"]
        self.assertIn(b"CCPL_DOCK", last)
        self.assertIn(b"signature_sha3_256", last)
        self.assertTrue(n.vault.verify_chain())
    def test_k2b_tamper_wrong_key_replay_all_fail(self):
        import copy
        from skn.ccpl import verify_dock, sign_manifest
        n, other = self.dock("SKN-001"), self.dock("SKN-009")
        rec = n.last_dock_record
        for field, value in (("target_id", "SKN-666"), ("pose", [9.0] * 6), ("nonce", "00" * 16)):
            bad = copy.deepcopy(rec); bad["manifest"][field] = value
            self.assertFalse(verify_dock(bad, n.dock_public_key)[0], field)
            # an attacker who also recomputes the digest still fails on the signature
            import hashlib
            from skn.ccpl import canonical
            bad["manifest_sha3_512"] = hashlib.sha3_512(canonical(bad["manifest"])).hexdigest()
            self.assertEqual(verify_dock(bad, n.dock_public_key)[1], "signature does not verify")
        self.assertFalse(verify_dock(rec, other.dock_public_key)[0])
        seen = set()
        self.assertTrue(verify_dock(rec, n.dock_public_key, seen)[0])
        self.assertEqual(verify_dock(rec, n.dock_public_key, seen)[1], "nonce already seen (replay)")
    def test_k2c_fails_closed_without_the_library(self):
        from skn import ccpl
        from skn.node import SKNV1_SovereignNode
        saved, ccpl.ML_DSA_65 = ccpl.ML_DSA_65, None
        try:
            n = SKNV1_SovereignNode("SKN-001", np.zeros(6, np.float32))
            depth = n.vault.chain_length
            ok, why = n.ccpl_initiate_dock("SKN-002", np.eye(3, dtype=np.float32), np.zeros(3, np.float32))
            self.assertEqual((ok, n.c_cpl_locked, n.vault.chain_length), (False, False, depth))
            self.assertIn("unavailable", why)
        finally:
            ccpl.ML_DSA_65 = saved


class TestLiveDashboard(unittest.TestCase):
    """skn_orbital_tui.py shows only computed values: run it headless and check them."""
    def test_plain_frames_show_real_state(self):
        import subprocess
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        p = subprocess.run([sys.executable, os.path.join(root, "skn_orbital_tui.py"), "--plain", "--frames", "101"],
                           capture_output=True, text=True, timeout=600)
        self.assertEqual(p.returncode, 0, p.stderr)
        last = p.stdout.strip().split("[ SKN-V1")[-1]
        self.assertIn("pieces b0 = 1", last)
        self.assertIn("holes  b1 = 1", last)
        self.assertIn("verify_chain OK", last)
        from skn import ccpl
        if ccpl.available():
            self.assertEqual(last.count("sig VALID"), 6)

if __name__ == "__main__":
    unittest.main(verbosity=2)
