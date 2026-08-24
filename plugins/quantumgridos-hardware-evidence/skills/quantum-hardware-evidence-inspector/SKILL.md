---
name: quantum-hardware-evidence-inspector
description: Inspect a quantum experiment by retrieving separate intent, capability, compilation, execution, and evidence records; read logical-to-physical transpilation mappings; and bound simulator or hardware claims. Use when reviewing source-to-ISA transformations, backend-target compatibility, measurement decoding, SDK execution provenance, or claims of physical-QPU evidence. Keep the workflow read-only; never discover live backends, authenticate, submit, cancel, rerun, reserve, or change provider state.
---

# Quantum Hardware Evidence Inspector

Review the supplied experiment through five linked records. Preserve missing facts instead of replacing them with plausible provider details.

## 1. Establish evidence class and authority

Classify every supplied result as exact analytical or statevector output, finite-shot ideal simulation, noisy simulation or mock-backend output, provider simulator evidence, physical-QPU evidence, or an explicitly synthetic training fixture.

Operate read-only. Do not authenticate, discover live backends, submit, cancel, rerun, reserve, spend credits, or modify a record. Do not infer physical execution from a backend-like interface, job-shaped object, or plausible count dictionary.

## 2. Retrieve only named records

When the `quantumgridos_hardware_evidence` MCP tools are available and the user provides record identifiers, use:

1. `get_experiment_intent`;
2. `get_backend_capability_snapshot`;
3. `validate_compilation_record`;
4. `get_execution_record`;
5. `get_evidence_record`.

Do not guess identifiers or paths. The server intentionally has no listing, search, provider-network, write, or submission tool. Read [the five-record contract](references/five-record-contract.md) when checking fields and references.

## 3. Read transpilation in four passes

1. **Intent:** identify logical wires, preparation, entangling operations, measurements or observables, classical order, and the output invariant.
2. **Layout:** reconstruct initial and final logical-to-physical placement, workspace positions, and the physical-measurement-to-classical-bit map.
3. **ISA:** check native operation support and two-qubit edges against the exact target snapshot; report depth and native two-qubit count without searching for source gate names inside decompositions.
4. **Evidence:** separate an exact behavioral check from a finite-shot decoding check, and state what each check does and does not prove.

Never infer layout or bit order from a drawing. Treat failed compilation invariants as errors rather than noise.

## 4. Distinguish repetition scopes

Separate Python construction loops, compiler candidate loops, shots within one execution, and experiment repetitions. For each, name the repeated object, output artifact, stopping rule, and owning record. A provider queue changes waiting time; it is not an algorithmic loop.

## 5. Bound conclusions

Report retrieval digests, passed and failed invariants, unsupported causal claims, the narrowest supported conclusion, and evidence required for a stronger conclusion. Keep application validation separate from provider execution and mitigation.

The packaged demo records are synthetic training fixtures. Never cite them as evidence that QuantumGridOS or any provider executed on a physical QPU.

