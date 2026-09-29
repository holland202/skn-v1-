# partition_veritas

**Experimental / unvalidated integration.**

Research experiment that tests whether SKN coordination, Companion triage, Veritas authority boundary, and dynamical constraint geometry compose under simultaneous communication loss and node failure.

This package does **not** modify production SKN semantics. It consumes existing interfaces through an adapter layer.

```
existing SKN
      │
      ├── topology / state
      ├── evidence vault
      ├── signatures
      └── node events
             │
             ▼
      experiment adapter
             │
       ┌─────┴─────┐
       ▼           ▼
 checkpoint     adversary
 recovery       injection
       │           │
       └─────┬─────┘
             ▼
       Veritas verifier (stub / external)
             │
      ALLOW / DEFER / REFUSE
             │
             ▼
          metrics + evidence bundle
```

## Layout

| File | Role |
|------|------|
| `PREREGISTRATION.md` | Frozen hypothesis, conditions, metrics, language |
| `protocol.py` | High-level experiment state machine |
| `checkpoint.py` | Checkpoint emission from SKN state + vault |
| `fragment_store.py` | Boring majority replication (not Reed-Solomon) |
| `recovery.py` | Reconstruct + demand independent verification |
| `adversary.py` | Registered adversarial injections |
| `metrics.py` | Counters + machine-readable evidence bundle |
| `run_experiment.py` | CLI entry point |
| `results/` | Output directory for bundles |

## Run

From the repository root:

```bash
python -m experiments.partition_veritas.run_experiment --seed 42 --nodes 8
```

Requires the existing `skn` package. Companion / Veritas components are optional adapters; when absent the experiment records `NEVER_WIRED` / `DEFER` rather than fabricating authority.

## Status language

- A violation → the registered protocol fails the specified invariant under the registered threat model.
- Zero violations → zero observed violations under the registered experimental conditions.

Do not promote either result to a general capability claim.
