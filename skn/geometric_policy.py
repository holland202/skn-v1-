"""Geometric policy: nearest-neighbour selection under the Bures distance.

Not currently imported by skn/__init__.py. Kept as a candidate policy layer.

Corrected 2026-08-10. The previous version computed np.sqrt(rho) elementwise
on a density matrix. That is not the matrix square root, so the function did
not compute the Bures distance. It agreed with the true value when rho was
diagonal and returned nan otherwise. It also ran a print() at import time.
"""
import numpy as np


def _sqrtm_psd(a):
    """Matrix square root of a Hermitian positive-semidefinite matrix."""
    w, v = np.linalg.eigh(a)
    w = np.clip(w, 0.0, None)
    return (v * np.sqrt(w)) @ v.conj().T


def fidelity(rho, sigma):
    """Uhlmann fidelity F = (tr sqrt(sqrt(rho) sigma sqrt(rho)))^2, in [0, 1]."""
    sr = _sqrtm_psd(np.asarray(rho, dtype=complex))
    inner = _sqrtm_psd(sr @ np.asarray(sigma, dtype=complex) @ sr)
    return float(np.clip(np.real(np.trace(inner)) ** 2, 0.0, 1.0))


def bures_distance(rho, sigma):
    """Bures distance sqrt(2 (1 - sqrt(F))). Zero iff rho == sigma."""
    return float(np.sqrt(max(0.0, 2.0 * (1.0 - np.sqrt(fidelity(rho, sigma))))))


class GeometricPolicy:
    """Selects the neighbour closest to the local state in Bures distance."""

    def __init__(self, state=None):
        self.state = np.eye(2) / 2.0 if state is None else np.asarray(state)

    def decide(self, local, neighbors):
        if not len(neighbors):
            return 0
        return int(np.argmin([bures_distance(local, n) for n in neighbors]))


def _selftest():
    """Registered checks. P0 is anti-vacuity: the metric must be able to
    return a nonzero value, or every other check passes trivially."""
    I2 = np.eye(2) / 2.0
    up = np.array([[1, 0], [0, 0]], dtype=complex)
    dn = np.array([[0, 0], [0, 1]], dtype=complex)
    plus = np.array([[.5, .5], [.5, .5]], dtype=complex)
    checks = [
        ("P0 anti-vacuity: orthogonal pure states maximally distant",
         bures_distance(up, dn), np.sqrt(2.0)),
        ("P1 identical states give exactly zero", bures_distance(up, up), 0.0),
        ("P2 mixed state with itself gives zero", bures_distance(I2, I2), 0.0),
        ("P3 symmetry d(up,plus) == d(plus,up)",
         bures_distance(up, plus) - bures_distance(plus, up), 0.0),
        ("P4 fidelity of orthogonal pure states is zero", fidelity(up, dn), 0.0),
        ("P5 fidelity of a state with itself is one", fidelity(plus, plus), 1.0),
        ("P6 d(|+>, I/2) is finite, not nan (the old bug)",
         bures_distance(plus, I2), np.sqrt(2 * (1 - np.sqrt(0.5)))),
    ]
    ok = True
    for name, got, want in checks:
        good = abs(got - want) < 1e-9
        ok &= good
        print("  %-52s got %.12f  want %.12f  %s"
              % (name, got, want, "PASS" if good else "FAIL"))
    pick = GeometricPolicy().decide(up, [dn, plus, up])
    good = pick == 2
    ok &= good
    print("  %-52s got %d  want 2  %s"
          % ("P7 policy picks the identical neighbour", pick, "PASS" if good else "FAIL"))
    print("\n  %s" % ("all checks passed" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
