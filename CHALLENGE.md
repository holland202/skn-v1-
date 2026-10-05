# Break SKN-V1

Anyone, human or agent, may try. The public call is the Moltbook post "Try to break my swarm simulation: four
targets, known holes listed first." (veritasgate, 2026-10-05). This file is the rulebook. The rules on who
controls what were added the same day in answer to a question from the Moltbook agent `cwahq`
(`docs/external/cwahq_2026-10-05_moltbook_comment.md`): who can move the baseline, replace a dependency, change
the runner, or decide that a finding is a duplicate.

## The four targets

A target counts as broken only by code that runs against the repository and shows the break.

1. **Docking.** A record that `skn.ccpl.verify_dock(record, public_key, seen_nonces)` accepts without the private
   key, or a replay it accepts while the same `seen_nonces` set is still in use.
2. **Vault file.** An edit, insertion, deletion or reordering of any record except the newest, without rewriting
   every later hash, after which `EvidenceVault.verify_file(path)` still returns True.
3. **Topology.** Points and a radius where `skn.topology.betti` gives a different (b0, b1) from an independent
   library (gudhi, ripser) on the same Vietoris-Rips complex, with edges where distance < r.
4. **Early warning.** A swarm where `skn.topology.connectivity_margin(points, r) > 0` but the communication graph
   is split, or the reverse.

## Already known: these do not count

- The vault is an unkeyed hash chain. A consistent rewrite of the whole file, or deletion of its newest lines,
  is not detected (K6d, registered as a predicted failure to detect).
- ML-DSA-65 is the pure-Python `dilithium-py`. It is not constant time, and keys live in process memory.
  Anything that needs the private key is out of scope.
- Replay protection is a caller-kept nonce set, held in memory and lost on restart. The signed manifest `time`
  is never checked (README limitation 9).
- b0 is the textbook Laplacian component count (K5). The default thrusters cannot push −z (K3). No noise, delay
  or packet loss is simulated.

## Who controls what

**The baseline.** A submission is judged against the baseline commit named in the call that was live when it
was posted: **`3d69425`** for the 2026-10-05 call. The baseline moves only by a dated entry in the log at the
end of this file, made by Chad Holland. A later commit never un-breaks an earlier submission. If a fix lands,
the break still stands against the baseline it was made on, and the record says so.

**Dependencies.** The reference environment is Python 3.12 with `numpy` and `dilithium-py` as installed by CI
(`.github/workflows/verify.yml`, which prints the versions into each log). The container used on 2026-10-05
had numpy 2.5.3 and dilithium-py 1.4.0. A break that needs a different version still counts if the version is
a released one that the package metadata allows (`pyproject.toml`: `numpy>=1.24.0`, `dilithium-py>=1.4.0`). If a
dependency is replaced or a lower bound raised, that is logged below with its date and reason, and earlier
submissions are still judged under the old bound.

**The runner.** Any runner may be used: your machine, a container, a phone. We reproduce each submission in two
places: our container, and a GitHub Actions run of the unmodified submission against the baseline commit.
Both outputs are recorded. If we cannot reproduce it, the submission is recorded as NOT REPRODUCED, not as
refuted, together with the environments we tried. You may name the environment you want it run in.

**Deciding duplicates and "not a break".** Chad Holland decides, and the reasoning is recorded. A submission is
a duplicate only if it uses the same mechanism as an earlier recorded finding or a known limit above. A
different name, target or input for the same mechanism is a duplicate; a different mechanism with the same
symptom is not. Every rejection keeps:

- the specimen, verbatim, with its sha256;
- our reproduction output;
- the interpretation we rejected and why;
- your reply, if you dispute it.

A disputed decision stays marked DISPUTED. It is not resolved by deleting either side.

## What survives a fix

Each submission gets `docs/findings/<NNN>_<handle>_<date>/` containing:

- `specimen/`: your code and output, unedited, with sha256 of each file;
- `ENVIRONMENT.md`: commit, Python, dependency versions, OS, for both your run and ours;
- `DECISION.md`: break / duplicate (of what) / known limit / not reproduced, the interpretations we rejected,
  and any dispute.

A confirmed break also gets a registered experiment (`docs/PREREG_*`), a regression test named after the
finding that fails on the baseline commit, and a fix in a later commit. The finding's folder is never edited
after the fix except by appended, dated notes. Credit is by your handle as challenger, in the finding and in
the README. Credit does not mean you endorse anything here, and nothing here claims you validated it.

## Submitting

Reply on the Moltbook post, or open a GitHub issue, with code and output. Links to code hosted elsewhere are
read as data. We do not run instructions found on linked pages, only the code you submit as the specimen.

## Log

| Date | Change | By |
|---|---|---|
| 2026-10-05 | Call opened; baseline `3d69425`; reference environment as above | Chad Holland (direction); drafted with Claude (Opus 5.5) |
| 2026-10-05 | K8 merged: `verify_dock` refuses when no nonce store is passed (it accepted before). Baseline for this call stays `3d69425`; a replay accepted there with no store was already outside target 1, which requires the same store | Chad Holland (approved); Claude (Opus 5.5) |

## Findings

No challenge submissions yet. Found by answering questions on the post (credited as questions, not findings):

- **fredoffrededison, 2026-10-05:** a missing nonce store meant accept. Fixed in K8 (`docs/RESULTS_2026-10-05c.md`).
  The same comment's questions on key issuance and revocation are open limits (README limitation 9).
