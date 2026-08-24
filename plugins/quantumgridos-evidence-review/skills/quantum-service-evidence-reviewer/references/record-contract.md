# Five-record contract

The MCP server reads one JSON object from each of five fixed directories below its configured records root. It accepts a `record_id`, not a filesystem path.

| Tool | Directory | Authoritative concern |
|---|---|---|
| `get_request_record` | `requests/` | Caller intent and requested evidence |
| `get_execution_plan` | `plans/` | Approved immutable execution plan |
| `get_job_snapshot` | `jobs/` | Service lifecycle and linked provider state |
| `get_result_record` | `results/` | Raw and derived evidence |
| `get_operations_summary` | `operations/` | Traces, metrics, retries, caches, and incidents |

Every file name is `<record_id>.json`. A record identifier contains only letters, digits, period, underscore, and hyphen, is at most 128 characters long, and cannot begin with punctuation. Every JSON object must contain a `record_id` that exactly matches its file name.

## Minimum useful fields

These fields are a review contract, not a claim that the current QuantumGridOS Python library already persists them.

### Request record

- `record_id`
- `schema_version`
- `service_request_id`
- `authorization_reference`
- `idempotency_key`
- `intent_hash`
- `requested_evidence_contract`
- `backend_selection_policy`
- `created_at`

### Plan record

- `record_id`
- `schema_version`
- `service_request_id`
- `plan_hash`
- `capability_snapshot`
- `compilation_hash`
- `execution_mode`
- `provider_scope`
- `quota_policy`
- `retry_policy`
- `result_destination`
- `approval_reference`
- `created_at`

### Job snapshot

- `record_id`
- `schema_version`
- `service_job_id`
- `service_request_id`
- `plan_record_id`
- `service_state`
- `provider_job_id`
- `provider_state`
- `submission_attempts`
- `reconciliation_state`
- `transitions`
- `terminal_reason`
- `observed_at`

### Result record

- `record_id`
- `schema_version`
- `service_job_id`
- `plan_record_id`
- `raw_result_reference`
- `provider_metadata`
- `evidence_class`
- `uncertainty`
- `derived_transformations`
- `application_validation`
- `provenance_hashes`
- `created_at`

### Operations summary

- `record_id`
- `schema_version`
- `service_job_id`
- `trace_references`
- `metrics_summary`
- `log_references`
- `cache_decisions`
- `retry_count`
- `incident_references`
- `redaction_state`
- `service_version`
- `observed_at`

Use `null`, `unknown`, or `not_supplied` for an absent fact. Never fill a missing field with a plausible provider value.

## Nested execution cross-check

The five records should make every supplied repetition boundary traceable. The plan should identify the source and compiled circuit artifacts, parameter bindings, target snapshot, shot or precision contract, execution grouping, stopping or budget policy, and checkpoint policy that define the work. The job should distinguish service transitions, provider jobs, batches or sessions, polling observations, submission attempts, and reconciliation events. The result should distinguish raw shot-level or aggregate evidence from classical parameter updates and application validation. The operations record should carry polling, retry, timeout, and reconciliation evidence without presenting those events as quantum execution.

If the records use the words `loop`, `iteration`, `execution`, `retry`, or `run` without naming the repeated object and owner, mark the boundary as ambiguous. Do not infer that a poll created a new job, that a retry was safe, that a shot updated parameters, or that a provider job was a complete experiment.

## MCP response envelope

Each successful tool call returns:

- `recordKind`: one of `request`, `plan`, `job`, `result`, or `operations`;
- `recordId`: the requested identifier;
- `sourcePath`: the relative path within the configured records root;
- `sha256`: the digest of the exact bytes read;
- `record`: the parsed JSON object.

The server rejects traversal syntax, files outside the configured root, files larger than 1 MiB, malformed JSON, non-object JSON, and an internal `record_id` that differs from the requested identifier. It has no write or provider-network capability.
