# Five-record contract

| Tool | Directory | Authoritative concern |
|---|---|---|
| `get_experiment_intent` | `intents/` | Logical experiment and measurement contract |
| `get_backend_capability_snapshot` | `capabilities/` | Timestamped target and execution limits |
| `validate_compilation_record` | `compilations/` | Source-to-ISA transformation and mappings |
| `get_execution_record` | `executions/` | Provider or simulator execution provenance |
| `get_evidence_record` | `evidence/` | Raw values, uncertainty, transformations, and conclusion |

Every file is named `<record_id>.json`; its JSON object contains the same `record_id`. Record identifiers contain only letters, digits, period, underscore, and hyphen, cannot begin with punctuation, and are at most 128 characters long.

The compilation validator reads only the named compilation record and its exact referenced intent and capability records. It checks source and target hashes, supported operations, two-qubit coupling edges, unique initial and final physical placements, and consistency between the final layout and measurement map. A passed validator shows internal consistency of stored local records. It does not prove provider authenticity, physical execution, compiler correctness for arbitrary inputs, or scientific validity.

Every packaged fixture contains `evidence_status: synthetic_training_fixture`. Missing provider facts remain `null`, `unknown`, or `not_supplied`.

