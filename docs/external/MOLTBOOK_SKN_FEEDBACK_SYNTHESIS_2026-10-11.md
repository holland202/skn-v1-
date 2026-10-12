# Moltbook SKN-V1 external-feedback synthesis — replay state, physical resilience and custody

**Record type:** external-feedback intake + proposed research question; **not an experiment or a new challenger finding**.  
**Prepared:** 2026-10-11 by ChatGPT (OpenAI) at Chad Holland's request. Human review: pending.  
**Subject:** SKN-V1 prototype (simulation only; **no physical swarm or radio hardware**).  
**Research governance:** [Principia Artificialis METHOD.md](https://github.com/holland202/principia-artificialis/blob/main/METHOD.md), WORKFLOW.md, CONTROLS.md govern any subsequent experiments. This note does not register or authorize a run.  
**Canonical challenge:** [CHALLENGE.md](../../CHALLENGE.md), baseline commit `3d69425` for the 2026-10-05 call. This note does not change the baseline or redefine what counts as a challenger finding.

## 1. Evidence/provenance inventory

Existing repository evidence (first-party research records, **not independent replication**):

- [Original Moltbook challenge](https://www.moltbook.com/post/98d45e9f-2ed4-4ab3-8e0f-86faf9d1e42f), `veritasgate`, 2026-10-05; its conditions are preserved in [CHALLENGE.md](../../CHALLENGE.md).
- [fredoffrededison's verbatim Moltbook questions and SHA-256](fredoffrededison_2026-10-05_moltbook_comment.md): who issues docking keys, can ejected members reuse keys, and what happens when the nonce store is unavailable. Credited as *questions*; no claim that the commenter submitted reproducible exploit code or endorsed the project.
- [cwahq's verbatim comment and SHA-256](cwahq_2026-10-05_moltbook_comment.md): custody of baseline, dependencies, runner, duplicate decisions; answered procedurally by [CHALLENGE.md](../../CHALLENGE.md). This commenter is identified in repo records as `cwahq` (not `cwah`).
- [K8 preregistration](../PREREG_2026-10-05c.md), [K8 results](../RESULTS_2026-10-05c.md), and [merged fix `6ba76e6`](https://github.com/holland202/skn-v1-/commit/6ba76e659c1ab1d7bb2a768df73746b226d0d377).
- [K9 preregistration](../PREREG_2026-10-05d.md) and [K9 results](../RESULTS_2026-10-05d.md); K9 was a separate candidate `check_fresh` mechanism, **not** a persistent replay store or a claim that `verify_dock` enforces freshness by default.
- User-supplied screenshots of Moltbook thread/commentary (supplied in a ChatGPT conversation, not copied to this repository). Screenshot SHA-256 values, identifying the *images* but not authenticating Moltbook's source data:
  - Main `@dynamo` post screenshot: `1f5e2c40f14582db4973f4120fe7f8c7e6ca0f3170bdd369606a2d6328ce89c5`.
  - SKN challenge/page screenshots: `45668e2ca74c5122a91f258807395211f6c6a62601481d8311e8e4f76f5a6eef`, `a1bef2ae84c018a21ea28833c7e2a576ecbb605ffbe2a6324b6cf03df8411597`, `da95d4aa02eabbcc885d73da8d533b75bce5b6c2982a4fc141d49ab261da5c8a`.
  - These are identification digests only; screenshots are **not archived here**, and exact comment IDs/URLs or independent API authenticity for all visible discussion are **ACCESS_UNVERIFIED**. Preserve originals separately before treating them as full C-EXT-provenance.
- The screenshot of a post by account `@dynamo` shows the headline **"Software swarm simulations provide zero kinetic security value."** (visible verbatim heading, not a validated statement). The argument concerning power draws, thermal envelopes, voltage sag, DC-bus jitter and energy-to-compute ratio is **paraphrased from the screenshot**, not presented as a cryptographic transcript or a verified hardware finding. Exact Moltbook post ID, full text and retrieval timestamp: **not established**.

These external opinions are research questions and criticism, not automatic verification, endorsement, or a new reproducible challenger submission. No external comment is an authorization for code changes.

## 2. Findings and dispositions

| ID | Source / question | Observation or repository fact | Disposition (as of this review) |
|---|---|---|---|
| EXT-SKN-01 | `fredoffrededison`: nonce-store unavailable | Before K8, `verify_dock` accepted an otherwise valid signed record repeatedly when no store was passed. K8 changes that absence to refusal; merged in `6ba76e6`. K8's frozen result is **4 of 5 as registered; K8e REFUTED**, not a clean 5/5. | **FIXED IN LIMITED SCOPE, SELF-TESTED**; no claim of restart protection or independent confirmation. |
| EXT-SKN-02 | `fredoffrededison`: key issuance, membership and revocation | K8 results explicitly say the verifier trusts the public key its caller supplies and has no membership/issuer/revocation/rotation mechanism. | **OPEN DESIGN/SECURITY LIMIT**, not demonstrated theft or Sybil exploit. |
| EXT-SKN-03 | Thread discussion: replay across process restarts | The caller-kept nonce set lives in memory. K8 results/README say a restart loses it; K9 results say the candidate marks also live in memory. | **OPEN / NOT TESTED AS NEW PERSISTENCE EXPERIMENT**. Known and disclosed limitation; not counted as new challenge finding. |
| EXT-SKN-04 | `@dynamo`: voltage, energy, thermal and bus-jitter constraints | SKN-V1 has simulation-only topology, cryptographic checks and a local benchmark; no physical swarm or hardware fault-injection evidence. | **PHYSICAL RESILIENCE NOT DEMONSTRATED**. Specific engineering concern; no measured hardware effect. |
| EXT-SKN-05 | `@dynamo`: simulations have "zero kinetic security value" | A simulation can expose software/protocol failures but cannot by itself validate physical actuation, power delivery, or deployment resilience. | **UNSUPPORTED UNIVERSAL ASSERTION**. Do not claim simulation proves hardware security either. |
| EXT-SKN-06 | `cwahq`: who controls experimental evidence | CHALLENGE.md explicitly assigns baseline `3d69425`, dependency/runner rules, Chad's decisions, duplicate definitions, and future findings folders. | **PROCEDURAL RULES DOCUMENTED; ENFORCEMENT NOT INDEPENDENTLY AUDITED**. |
| EXT-SKN-07 | K9 freshness candidate (relevant prior work) | K9 `check_fresh` results: **5 of 6 as registered; P4 REFUTED** because frozen clock and expected 100/100 acceptance contradicted. Strict mark accepted 12/1000 shuffled legitimate records; no persistence or device validation. | **LIMITED SELF-TESTED RESULT + REFUTED REGISTRATION; KEEP BOTH**. Do not report it as full replay defense. |

The canonical [CHALLENGE.md](../../CHALLENGE.md) calls a code-backed reproduction against a specified target a **finding**. Questions and critiques without reproducible submissions are **probes**, or outside-design suggestions, and are credited without implying endorsement. This synthesis does not add a numbered challenge finding or modify existing dispositions.

## 3. Cross-cutting failure hypothesis — not observed as an exploit

**HYPOTHESIS:** A previously accepted genuine signed docking record may be accepted again after simulated process restart if replay state is held only in volatile memory; a cryptographically valid signature does not itself prove freshness.

Illustrative sequence (unexecuted for this proposed study):

1. A genuine docking record is signed and accepted, with the nonce recorded in an in-memory store.
2. An operator simulates a brownout / process termination or forces the service to restart.
3. The verifier is reconstructed with a fresh in-memory nonce set. The signature is still valid and the nonce has no remembered history.
4. The old signed record is presented again. **Question:** will the rebuilt verifier accept it, and would a separately attached executor cause a repeated effect?

**Important distinctions:** Repository documentation already states that the memory-only store is lost on restart; this hypothesis is not a newly established flaw or reproduced attack. An actual repeated physical effect is *not* claimed or tested. This model does not show that a real voltage sag happened, or that all real-world swarm faults occur at power interfaces.

## 4. Possible next experiment (DESIGN SKETCH; NOT PREREGISTERED OR AUTHORIZED)

**Working identifier:** `SKN-PERSIST-001` (proposal name only; do not reuse as an approved W2 registration).  
**Question:** After a controlled process restart, do old signed docking records remain refused without causing invalid refusals of first-time legitimate records, across missing, available, corrupted or interrupted replay-state persistence?

Candidate paired arms:

- **Existing control:** in-memory nonce history, restarted between two presentations of the same signed record.
- **Proposed persistence arm:** explicitly serialized and restored state, with a defined crash-consistency policy and fail-closed handling if the state cannot be loaded. No implementation is authorized here.
- **Anti-vacuity controls:** a *new* valid record with valid authority must be accepted in the permitted case; a repeated signed record must be refused; a tampered signature and a missing/unreadable store must be refused for their own reasons, with observable distinctions.
- **Adversarial boundaries:** crash just before and after state commit; torn/corrupt state; rollback/truncation of stored state; restart with new process; stale clock; legitimate out-of-order delivery. Document when persistence can and cannot survive adversary-controlled file rollback.
- **Evidence to capture:** frozen PA methodology commit, original SKN baseline and revised candidate commit, exact harness source hashes, commands, stderr/stdout, exit codes, environment, state-image hashes, sabotage runs, known positive and negative outcomes and independent-review status.
- **Next physical phase (separate):** instrumented hardware brownout, thermal and power-budget testing only after a real hardware substrate exists and its limits are registered.

**Required human decision before study:** Chad must approve the scientific question, simulation environment, case matrix, controls and allowed code changes. K8/K9 results cannot be retrospectively re-scored. Per PA W2, freeze a new preregistration *before* building/running a confirmatory instrument.

## 5. Proposed PA → VO → SV feedback intake — not integration

- **PA:** store this external criticism as questions and competing hypotheses; preserve evidence, falsifiers, controls, original failures and methodology commit.
- **VO:** *if separately authorized*, examine whether a preregistered persistence experiment distinguishes a real mechanism from plausible-sounding interpretation. VO has not prechecked this note.
- **SKN-V1:** correct experimental subject for replay-state persistence and physical limitations. **Do not label it an SV test**; SV is a separate AI action-governance project.
- **SV:** related conceptual issue—authorization and recorded execution are distinct—but **no SV code or contract change is authorized or implied**.
- **SRR-1:** can convey a pinned, read-only handoff if Chad later authorizes a pilot; no relay execution here.

## 6. Open provenance and decision items

- Original `@dynamo` post URL, full unedited body, timestamp, comment IDs and content hashes: **ACCESS_UNVERIFIED**; request them before claiming a verbatim archive.
- Screenshots currently identifiable by SHA-256 but **not stored in the repository**; preserve originals if full C-EXT compliance is required.
- Current state of any independent third-party reproduction of K8/K9: **NOT ESTABLISHED BY THIS REVIEW**.
- No new test or simulated restart was run for this intake. No CI results or physical observations are claimed.
- No rule, authority, case label, verified result, baseline, release or published external finding is changed by this document.

**Attribution:** source questions from `fredoffrededison` and `cwahq` as cited; resilience critique attributed to screenshot-visible `@dynamo`. ChatGPT synthesized; Chad directed documentation. Attribution does not imply that any outside party endorsed the interpretations, fixes or proposed experiment.
