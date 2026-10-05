"""Betti-1 topology guard, built (docs/PREREG_2026-09-27.md, K1).

Exact Betti numbers b0 and b1 of the Vietoris-Rips (flag) complex of the swarm at radius r, computed over
GF(2) from boundary-matrix ranks. Pure NumPy: no GUDHI, no ripser.

  vertices  = nodes
  edges     = pairs closer than r
  triangles = triples whose three edges are all present (the flag complex fills every 3-clique)
  b0 = V - rank(d1)
  b1 = (E - rank(d1)) - rank(d2)

Fragmentation of the swarm is b0 > 1. A hole in its coverage is b1 > 0. `graph_cycle_rank` is the count the
guard used before (E - V + C), kept for comparison: it is b1 of the communication *graph* and counts every
triangle of a fully connected formation as a hole.
Cost: O(n^3) triangles and a GF(2) elimination on them. Intended for swarms of tens of nodes.
"""
from itertools import combinations

import numpy as np


def _gf2_rank(M):
    """Rank over GF(2) of a 0/1 matrix, by row reduction."""
    A = (np.asarray(M, dtype=np.uint8) & 1).copy()
    rows, cols = A.shape
    r = 0
    for c in range(cols):
        if r == rows:
            break
        piv = np.nonzero(A[r:, c])[0]
        if piv.size == 0:
            continue
        p = r + piv[0]
        if p != r:
            A[[r, p]] = A[[p, r]]
        below = np.nonzero(A[:, c])[0]
        below = below[below != r]
        A[below] ^= A[r]
        r += 1
    return r


def rips_complex(points, r):
    """(n, edges, triangles) of the Vietoris-Rips complex at radius r (pairwise distance < r)."""
    P = np.asarray(points, dtype=float)
    n = len(P)
    D = np.linalg.norm(P[:, None, :] - P[None, :, :], axis=-1)
    adj = (D < r) & ~np.eye(n, dtype=bool)
    edges = [(i, j) for i, j in combinations(range(n), 2) if adj[i, j]]
    tris = [(i, j, k) for i, j, k in combinations(range(n), 3) if adj[i, j] and adj[i, k] and adj[j, k]]
    return n, edges, tris


def betti(points, r):
    """(b0, b1) of the Vietoris-Rips complex of `points` (n x d) at radius r."""
    n, edges, tris = rips_complex(points, r)
    if n == 0:
        return 0, 0
    eidx = {e: k for k, e in enumerate(edges)}
    d1 = np.zeros((n, len(edges)), dtype=np.uint8)
    for k, (i, j) in enumerate(edges):
        d1[i, k] = d1[j, k] = 1
    d2 = np.zeros((len(edges), len(tris)), dtype=np.uint8)
    for k, (i, j, l) in enumerate(tris):
        d2[eidx[(i, j)], k] = d2[eidx[(i, l)], k] = d2[eidx[(j, l)], k] = 1
    r1 = _gf2_rank(d1) if edges else 0
    r2 = _gf2_rank(d2) if tris else 0
    return n - r1, (len(edges) - r1) - r2


def graph_cycle_rank(points, r):
    """E - V + C of the communication graph: the count the guard used before K1 (not a Rips Betti number)."""
    n, edges, _ = rips_complex(points, r)
    if n < 2:
        return 0
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, j in edges:
        a, b = find(i), find(j)
        if a != b:
            parent[a] = b
    return len(edges) - n + len({find(i) for i in range(n)})


# ---- Standard connectivity signals, the rivals to the guard (docs/PREREG_2026-10-05b.md, K5) ----

def _adjacency(points, r):
    P = np.asarray(points, dtype=float)
    D = np.linalg.norm(P[:, None, :] - P[None, :, :], axis=-1)
    return D, (D < r) & ~np.eye(len(P), dtype=bool)


def components(points, r):
    """Number of connected components of the communication graph (union-find). Equals b0 (K5a)."""
    n = len(points)
    _, adj = _adjacency(points, r)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, j in zip(*np.nonzero(np.triu(adj))):
        parent[find(i)] = find(j)
    return len({find(i) for i in range(n)})


def laplacian_spectrum(points, r, weighted=False):
    """Eigenvalues (ascending) of the graph Laplacian. Weighted: w = 1 - d/r on each edge (d < r)."""
    D, adj = _adjacency(points, r)
    W = np.where(adj, 1.0 - D / r, 0.0) if weighted else adj.astype(float)
    L = np.diag(W.sum(axis=1)) - W
    return np.linalg.eigvalsh(L)


def algebraic_connectivity(points, r, weighted=False):
    """lambda_2 of the Laplacian (Fiedler 1973): 0 when disconnected, larger when more redundantly linked."""
    ev = laplacian_spectrum(points, r, weighted)
    return float(ev[1]) if len(ev) > 1 else 0.0


def connectivity_margin(points, r):
    """r minus the longest edge of the minimum spanning tree of all pairwise distances (Prim, O(n^2)).

    The graph at radius r (edges where d < r) is connected exactly when this is > 0. Unlike b0 it is
    continuous: it says how far the swarm is from fragmenting, in metres."""
    D, _ = _adjacency(points, r)
    n = len(D)
    if n < 2:
        return float(r)
    in_tree = np.zeros(n, dtype=bool)
    in_tree[0] = True
    best = D[0].copy()
    longest = 0.0
    for _ in range(n - 1):
        cand = np.where(in_tree, np.inf, best)
        k = int(np.argmin(cand))
        longest = max(longest, float(cand[k]))
        in_tree[k] = True
        best = np.minimum(best, D[k])
    return float(r) - longest
