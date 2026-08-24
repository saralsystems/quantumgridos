---
name: quantum-service-evidence-reviewer
description: Review a quantum-classical service by retrieving and separating its request, immutable plan, job, result, and operations records and mapping its nested execution loops. Use when auditing asynchronous quantum APIs, shots, algorithm iterations, polling, retries, idempotency, provider adapters, caches, observability, reproducibility, or QuantumGridOS service boundaries. Keep the workflow read-only; never submit, cancel, rerun, reserve, authenticate, or change provider state.
---

# Quantum Service Evidence Reviewer

Use the five-folder model. Treat each record as a separate source of authority, and preserve the links among them without combining them into one ambiguous job object.

## 1. Establish scope and authority

Identify the service boundary, the supplied record identifiers, and the conclusion the user wants to evaluate. State whether the review is based on source, configuration, stored records, simulator output, or physical-hardware evidence. Mark missing facts as `unknown` or `not supplied`.

Operate read-only. Do not authenticate, submit, cancel, rerun, reserve capacity, rotate credentials, change configuration, or spend provider credits. If the requested outcome requires any such action, separate it from the review and ask for explicit authorization.

## 2. Retrieve only named records

When the `quantumgridos_records` MCP tools are available and the user supplies record identifiers, call the matching focused tools:

1. `get_request_record` for the request;
2. `get_execution_plan` for the immutable plan;
3. `get_job_snapshot` for service and provider state;
4. `get_result_record` for raw and derived evidence;
5. `get_operations_summary` for traces, metrics, retry, cache, and incident evidence.

Do not guess identifiers. Do not ask the MCP server to discover arbitrary files: it intentionally exposes no search, listing, path, write, or provider-execution tool. If a record is unavailable, retain the gap in the review.

Read [the record contract](references/record-contract.md) when mapping fields, checking cross-record links, or interpreting a tool error.

## 3. Build the five-record ledger

Create five distinct sections:

- **Request:** service request ID, authorization reference, idempotency key, intent hash, requested evidence contract, backend-selection policy, creation time, and schema version.
- **Plan:** request link, capability snapshot, compilation hash, execution mode, provider and region scope, quota policy, retry policy, result destination, approval reference, and plan hash.
- **Job:** service job ID, plan link, provider job ID when known, append-only transitions, submission attempts, reconciliation state, timestamps, and terminal reason.
- **Result:** job and plan links, immutable raw-result reference, provider metadata, evidence class, uncertainty, transformations, application validation, and provenance hashes.
- **Operations:** correlated service job, traces, low-cardinality metrics, structured logs, cache decisions, retries, incidents, redaction state, and service version.

Record each MCP response SHA-256 digest as retrieval provenance. The digest proves which stored file was read; it does not prove that the statements inside the file are true.

## 4. Map nested execution and repetition

Build a loop ledger for every supplied repetition boundary. For each boundary, record the repeated object, owner, input, output, stopping rule, authoritative record, and whether it creates new quantum evidence. Check explicitly for:

- Python construction loops over circuit fragments, observables, or parameter sets;
- compiler candidate search over layouts, routes, or rewrites;
- shot repetition of one freshly prepared compiled circuit;
- provider jobs and any batch or session grouping;
- classical optimizer or domain-algorithm updates;
- provider polling;
- service retry or uncertain-submission reconciliation;
- complete experiment replication under a declared protocol.

Keep gates, circuits, shots, provider jobs, and classical iterations distinct. Polling changes service knowledge but does not create a new shot, provider job, or parameter update. A retry is an operational decision and must not silently become a second experiment.

## 5. Test invariants

Report each check as passed, failed, or not testable:

1. the same idempotency key and intent hash identify the same service job;
2. an immutable plan exists before provider submission;
3. an ambiguous submission is reconciled before another attempt;
4. service state and provider state remain separate but linked;
5. terminal state does not silently return to running;
6. a restarted worker can recover authoritative state;
7. cache identity contains every evidence-defining field;
8. raw results remain immutable when derived results change;
9. inspection authority is separate from submission or cancellation authority;
10. the result links to the exact request, plan, compilation, and execution evidence needed for the conclusion.

Treat an identifier, hash, schema, or lifecycle mismatch as an error, not as ordinary quantum noise.

## 6. Bound quantum claims

Distinguish exact computation, finite-shot ideal simulation, noisy simulation, provider simulation, and physical-QPU execution. A successful API response, worker completion, provider job, cache hit, or feasible decoded candidate does not by itself establish scientific validity, optimality, application value, or quantum advantage.

## 7. Return the review

Return:

1. scope and authority;
2. the five-record ledger with provenance digests;
3. the nested execution and loop ledger;
4. passed, failed, and untestable invariants;
5. duplicate-work, data-loss, secret, and observability risks;
6. unsupported quantum or application claims;
7. the narrowest conclusion supported by the records;
8. missing evidence required for a stronger conclusion;
9. safe read-only next checks;
10. state-changing actions that require separate authorization.

Never invent records, measurements, provider status, calibration data, citations, credentials, or hardware execution.
