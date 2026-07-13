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

if __name__ == "__main__":
    unittest.main(verbosity=2)
