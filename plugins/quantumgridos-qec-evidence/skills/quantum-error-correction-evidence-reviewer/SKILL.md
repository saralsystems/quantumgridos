---
name: quantum-error-correction-evidence-reviewer
description: Review quantum error-correction code specifications, syndrome records, decoder evidence, distance-scaling studies, and fault-tolerance claims. Use when auditing a QEC manuscript, notebook, experiment bundle, simulator result, hardware report, or QuantumGridOS integration. Do not use it to authenticate, submit hardware jobs, change live decoder settings, or apply device corrections.
---

# Quantum Error-Correction Evidence Reviewer

Review the supplied material as an algebraic code definition, an inference pipeline, and an evidence claim. Preserve unknowns and keep simulator, synthetic-noise, and hardware evidence separate.

## 1. Establish scope and authority

Identify supplied code definitions, circuits, mappings, syndrome data, noise or calibration records, decoders, logical results, comparators, and claims. State whether the review is source-only, simulation-backed, recorded-hardware-backed, or supported by a complete reproducibility bundle.

Default to read-only work. Do not authenticate, submit, cancel, rerun, recalibrate, modify live decoder weights, change device configuration, apply physical recovery, or spend provider credits without separate explicit authorization.

When the `quantumgridos_qec_evidence` MCP tools are available, retrieve only exact record identifiers supplied by the user. Use `inspect_code_spec`, `validate_syndrome_schema`, `compare_distance_runs`, `audit_fault_tolerance_claim`, and `export_qec_evidence_bundle` for their named record types. The export tool returns a digest manifest and performs no file or provider write. Do not guess identifiers or treat a record digest as proof that the statements inside the record are true.

## 2. Validate the code contract

Record n, k, declared distance, stabilizer generators, logical operators, boundaries, and supported error set. Check generator commutation, independence, logical commutation relationships, and any claimed X- and Z-distances. Distinguish a code-space definition from a fault-tolerant extraction circuit.

## 3. Reconstruct the six-stage loop

Create sections for encode, noise, syndrome extraction, decoding, frame update or physical recovery, and logical validation. For each stage, link the supplied artifact and mark absent details unknown.

## 4. Review syndrome and decoder evidence

Keep raw syndrome bits, detection events, decoder hypotheses, recoveries, frame updates, and logical outcomes as separate records. State the decoder's noise assumptions, information boundary, calibration source, version, latency, and treatment of boundaries, leakage, correlations, and measurement faults.

Trace at least one extraction circuit in three passes. The syntax pass lists each wire, ancilla preparation, controlled interaction, measurement, and classical destination in time order. The state pass states the parity or stabilizer invariant transferred to each ancilla and verifies that the logical amplitudes are not exposed. The evidence pass maps measured bits to named checks, round indices, decoder inputs, and frame conventions. Reject any circuit whose wire order, control-target direction, check assignment, or bit order is ambiguous.

Classify repetition explicitly as circuit construction, coherent interaction order inside one extraction round, repeated extraction rounds on one continuing logical memory, independent shots with fresh preparation, or classical decoder and calibration loops. Record what persists and resets at every boundary. Do not use `round`, `shot`, `cycle`, and `iteration` as interchangeable terms.

## 5. Classify the claim

Assign at most one highest supported rung: syndrome detection, corrected observable, break-even memory, repeated protected operation, below-threshold scaling, fault-tolerant logical operation, or validated logical algorithm. Postselection must be explicit and cannot be reported as deterministic correction.

Do not establish below-threshold behavior from one physical gate-error number. Require comparable increasing-distance experiments with a fixed task, circuit family, decoder contract, statistical method, and documented changes.

## 6. Check reproducibility and statistics

Require hashes or immutable references for code, scheduled circuits, noise and calibration records, raw syndrome batches, decoder configuration, logical results, and analysis. Record sample counts, accepted and rejected runs, uncertainty intervals, drift treatment, and comparator identity.

## 7. Produce the review

Return:

1. authority and evidence scope;
2. validated code contract and algebraic failures;
3. six-stage reliability map;
4. three-pass circuit trace and repetition-boundary ledger;
5. decoder and information-boundary findings;
6. highest supported evidence rung;
7. unsupported conclusions and claims that exceed the evidence;
8. reproducibility and statistical gaps;
9. bounded corrected conclusion;
10. safe read-only next checks and separately authorized state-changing actions.
