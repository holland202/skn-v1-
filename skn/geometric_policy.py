# Geometric Policy Integration from QUASAR

import numpy as np

def bures_distance(rho, sigma):
    sqrt_rho = np.sqrt(rho)
    sqrt_sigma = np.sqrt(sigma)
    fidelity = np.trace(np.sqrt(sqrt_rho @ sigma @ sqrt_rho))
    return np.sqrt(2 * (1 - np.real(fidelity)))

class GeometricPolicy:
    def __init__(self):
        self.state = np.eye(2)

    def decide(self, local, neighbors):
        dists = [bures_distance(local, n) for n in neighbors]
        return np.argmin(dists) if dists else 0

print('GeometricPolicy integrated into SKN.')