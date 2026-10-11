# Azure ARM64 research results — October 11–12, 2026

**Status: AWAITING EVIDENCE.** This directory is an intake location, not a claim that the experiment has finished or passed.

## Study identification

- Repository: `holland202/skn-v1-`
- Source revision independently checked on the Azure VM before testing: `b6572169355985d52a5e71526702ecdab4abc451`
- Study focus: Swarm formation/topology and ML-DSA-65 docking integrity/replay simulations
- Compute substrate: `lde-test-03`, Azure Central US, `aarch64`, Ubuntu 24.04.4 LTS, Python 3.12.3
- Active campaign started UTC: `2026-10-11T21:56:19Z`
- Campaign evidence root on VM: `/home/azureuser/research/advanced-audit/azure24h/runs/unattended-20261011T215619Z`
- Earlier separately stopped run: `unattended-20261011T215443Z` (do not merge overlapping seeds)
- Runner deadline: `2026-10-12T21:08:00Z`; VM shutdown scheduled for `2026-10-12T21:28:00Z`. **Scheduled is not observed.**

## Evidence required before publication

1. Final or interruption-labeled run summary with per-project counts, seed coverage, and explicit PASS / FINDING / BLOCKED / INCOMPLETE definitions.
2. Source revision, runner/experiment version and SHA-256 manifest; exact commands, dependency versions, environment and machine identity.
3. Per-case results, errors, timeouts, exit codes, start/end times, and any failing cases, with provenance to the corresponding raw archive.
4. Negative results and known limitations, including evidence boundaries and sabotage/control outcomes, preserved without relabeling.
5. Independent verification status stated separately from execution success and from internal consistency.

Publish a compact report and hashes here. If raw outputs are too large for GitHub, store them in a stable evidence archive and include a retrievable link and checked SHA-256 inventory. Do not upload credentials or private SSH keys.

**Scientific status:** Exploratory campaign; no claim of independent validation or production readiness. Existing baseline and registered negative findings remain separate from new exploratory measurements.
