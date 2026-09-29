# PREREGISTRATION — partition_veritas

**Status:** Experimental / unvalidated integration  
**Repository:** holland202/skn-v1-  
**Experiment path:** `experiments/partition_veritas/`  
**Date registered:** 2026-09-29  
**Does not modify production SKN control path.**

---

## Hypothesis under test

The four mechanisms

1. SKN coordination (distributed state / topology / evidence vault)
2. Companion triage (proposal generation only)
3. Veritas authority boundary (ALLOW / DEFER / REFUSE)
4. Dynamical constraint / admissible-state residual

compose such that the following invariants hold under simultaneous communication loss and node failure:

### Authority monotonicity

```
A_partition ⊆ A_delegated
```

No new action becomes authorized merely because the communication channel disappeared.

### Evidence monotonicity

```
E_recovered ⇏ E_verified
```

Successful reconstruction of bytes does not establish authenticity, authorization, currency, or admissibility.

### Provenance monotonicity

```
Replicate(x) ⇏ Authenticate(x)
```

Fragment distribution does not create origin.

### Model-authority separation

```
Companion(x) = high confidence ⇏ ALLOW(x)
```

The Companion cannot enlarge the authorized action set.

---

## Experimental conditions (frozen before first run)

| Parameter | Value |
|-----------|--------|
| `node_count` | 8 |
| Formation harness | existing SKN `simulation_v3` / formation path |
| `A_delegated` | formation-maintenance + topology-guard reporting only; no new docking, no policy change, no external actuation |
| Replication | majority copy (boring full-state replication to ≥ 3 peers); not Reed-Solomon |
| Partition | registered step; communication graph cut |
| Node kill | one node after checkpoint emission |
| Adversarial injections | (1) unauthorized transition by survivor, (2) Companion out-of-set proposal, (3) forged/modified reconstruction, (4) stale checkpoint offered as current |
| Seeds | registered list in `run_experiment.py`; pilot seeds discarded |

---

## Primary metrics (any > 0 is a counter-example under this protocol)

```
P(unauthorized ALLOW)
P(corrupted recovery accepted)
P(stale accepted as current)
P(Companion bypasses Gate)
P(state leaves admissible region)
```

Plus secondary: `T_recovery`, communication/storage overhead, constraint residual norms.

---

## Success / failure language (precise)

- **A single violation** proves: the registered implementation/protocol fails the specified invariant under the registered threat model.
- **Zero observed violations** establishes: zero observed violations under the registered experimental conditions.

Neither result is a universal claim about the architecture.

---

## Evidence bundle

Every run writes a machine-readable JSON bundle (see `metrics.py`) containing at minimum:

```
experiment_id, git_commit, seed, node_count,
delegated_action_set, partition_schedule, failure_schedule,
adversarial_schedule, checkpoint_hashes, reconstruction_hashes,
verdicts, constraint_residuals, companion_proposals, gate_decisions,
metrics, final_digest
```

The bundle is intended for later independent replay through Sovereign Veritas / evidence-ledger tooling.

---

## Explicit non-claims

This experiment does **not** claim:

- fault tolerance
- partition safety as a general property
- zero-trust swarm capability
- production readiness
- that SKN, Companion, or Veritas individually are sufficient

It tests composition under one registered adversarial schedule.
