#!/usr/bin/env python3
"""Dependency-free, read-only MCP server for local quantum-advantage evidence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Union


SERVER_NAME = "quantumgridos-advantage-evidence"
SERVER_VERSION = "0.1.0"
LATEST_PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOL_VERSIONS = {
    "2024-11-05",
    "2025-03-26",
    "2025-06-18",
    "2025-11-25",
}
EVIDENCE_ENV = "QUANTUMGRIDOS_ADVANTAGE_EVIDENCE_DIR"
DEFAULT_EVIDENCE_ROOT = Path(__file__).resolve().parent.parent / "records"
MAX_RECORD_BYTES = 1024 * 1024
MAX_RECORDS_PER_CALL = 32
RECORD_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

JsonObject = Dict[str, Any]
JsonValue = Union[None, bool, int, float, str, List[Any], JsonObject]

KIND_DIRECTORIES = {
    "contract": "contracts",
    "baseline": "baselines",
    "experiment": "experiments",
    "gate": "gates",
    "ledger": "ledgers",
}

EVIDENCE_TYPES = {
    "mathematical_analysis",
    "exact_classical_computation",
    "stochastic_classical_simulation",
    "ideal_quantum_simulation",
    "noisy_quantum_simulation",
    "emulation",
    "physical_quantum_hardware",
    "plan_only",
}

CONTRACT_FIELDS = {
    "input_family",
    "required_output",
    "correctness_test",
    "approximation_rule",
    "counted_resources",
    "intended_user",
}

BASELINE_FIELDS = {
    "contract_digest",
    "algorithm",
    "implementation_version",
    "configuration",
    "environment",
    "stopping_rule",
    "validator_id",
}

EXPERIMENT_FIELDS = {
    "contract_digest",
    "evidence_type",
    "artifact_digest",
    "environment",
    "raw_output",
    "validator_id",
    "limitations",
}

HARDWARE_FIELDS = {
    "hardware_identity",
    "compilation",
    "calibration_context",
    "sampling_policy",
}

DECISION_REQUIREMENTS = {
    "learn": {"problem_contract"},
    "monitor": {"problem_contract", "review_trigger"},
    "reproduce": {
        "problem_contract",
        "artifact_identity",
        "environment",
        "validator",
    },
    "explore": {
        "problem_contract",
        "classical_baseline",
        "candidate_plan",
        "validator",
        "resource_boundary",
    },
    "pilot": {
        "problem_contract",
        "classical_baseline",
        "physical_or_operational_evidence",
        "independent_validation",
        "complete_resource_account",
        "user_outcome",
        "owner",
        "review_trigger",
        "stop_condition",
        "security_governance_review",
    },
    "deploy": {
        "problem_contract",
        "classical_baseline",
        "validated_production_evidence",
        "independent_validation",
        "complete_resource_account",
        "user_outcome",
        "owner",
        "review_trigger",
        "stop_condition",
        "security_governance_review",
        "operations_plan",
    },
}


class EvidenceReadError(ValueError):
    """A bounded error that is safe to return as a tool result."""


def evidence_root() -> Path:
    configured = os.environ.get(EVIDENCE_ENV)
    candidate = Path(configured) if configured else DEFAULT_EVIDENCE_ROOT
    return candidate.resolve(strict=False)


def validate_record_id(value: Any) -> str:
    if not isinstance(value, str) or RECORD_ID_PATTERN.fullmatch(value) is None:
        raise EvidenceReadError(
            "record identifiers must start with a letter or digit, contain only letters, "
            "digits, period, underscore, or hyphen, and be at most 128 characters"
        )
    return value


def read_record(kind: str, record_id: Any) -> tuple[JsonObject, JsonObject]:
    if kind not in KIND_DIRECTORIES:
        raise EvidenceReadError("unsupported record kind")
    validated_id = validate_record_id(record_id)
    root = evidence_root()
    relative = Path(KIND_DIRECTORIES[kind]) / (validated_id + ".json")
    target = (root / relative).resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise EvidenceReadError("record resolves outside the configured evidence root") from exc
    if not target.is_file():
        raise EvidenceReadError("record not found: {}".format(relative.as_posix()))
    try:
        if target.stat().st_size > MAX_RECORD_BYTES:
            raise EvidenceReadError("record exceeds the 1 MiB read limit")
        raw = target.read_bytes()
    except EvidenceReadError:
        raise
    except OSError as exc:
        raise EvidenceReadError("record could not be read") from exc
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceReadError("record is not a valid UTF-8 JSON document") from exc
    if not isinstance(parsed, dict):
        raise EvidenceReadError("record must contain one JSON object")
    if parsed.get("record_id") != validated_id:
        raise EvidenceReadError(
            "record_id inside the document does not match the requested identifier"
        )
    provenance = {
        "kind": kind,
        "recordId": validated_id,
        "sourcePath": relative.as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    return parsed, provenance


def ensure_arguments(arguments: Mapping[str, Any], expected: set[str]) -> None:
    extra = sorted(set(arguments) - expected)
    if extra:
        raise EvidenceReadError("unexpected argument(s): " + ", ".join(extra))


def missing_fields(record: Mapping[str, Any], required: set[str]) -> List[str]:
    missing = []
    for field in sorted(required):
        value = record.get(field)
        if value is None or value == "" or value == [] or value == {}:
            missing.append(field)
    return missing


def require_id_list(value: Any, field_name: str, minimum: int = 1) -> List[str]:
    if not isinstance(value, list) or not minimum <= len(value) <= MAX_RECORDS_PER_CALL:
        raise EvidenceReadError(
            "{} must contain between {} and {} identifiers".format(
                field_name, minimum, MAX_RECORDS_PER_CALL
            )
        )
    validated = [validate_record_id(item) for item in value]
    if len(set(validated)) != len(validated):
        raise EvidenceReadError("{} identifiers must be unique".format(field_name))
    return validated


def read_problem_contract(arguments: Mapping[str, Any]) -> JsonObject:
    ensure_arguments(arguments, {"contract_id"})
    record, provenance = read_record("contract", arguments.get("contract_id"))
    missing = missing_fields(record, CONTRACT_FIELDS)
    resources = record.get("counted_resources")
    findings: List[str] = []
    if not isinstance(resources, list) or not resources or not all(
        isinstance(item, str) and item.strip() for item in resources
    ):
        findings.append("counted_resources must be a non-empty array of strings")
    if missing:
        findings.append("missing required fields: " + ", ".join(missing))
    return {
        "tool": "read_problem_contract",
        "status": "pass" if not findings else "incomplete",
        "provenance": [provenance],
        "contractDigest": provenance["sha256"],
        "record": record,
        "missingFields": missing,
        "findings": findings,
        "limitations": [
            "A complete schema does not prove that the task or acceptance test is appropriate."
        ],
    }


def list_baselines(arguments: Mapping[str, Any]) -> JsonObject:
    ensure_arguments(arguments, {"baseline_ids", "contract_digest"})
    baseline_ids = require_id_list(arguments.get("baseline_ids"), "baseline_ids")
    expected_digest = arguments.get("contract_digest")
    if expected_digest is not None and (
        not isinstance(expected_digest, str)
        or re.fullmatch(r"[a-f0-9]{64}", expected_digest) is None
    ):
        raise EvidenceReadError("contract_digest must be a lowercase SHA-256 value")
    rows = []
    provenance = []
    findings = []
    for baseline_id in baseline_ids:
        record, source = read_record("baseline", baseline_id)
        provenance.append(source)
        missing = missing_fields(record, BASELINE_FIELDS)
        digest_matches = expected_digest is None or record.get("contract_digest") == expected_digest
        if missing:
            findings.append(
                "{} is missing {}".format(baseline_id, ", ".join(missing))
            )
        if not digest_matches:
            findings.append("{} uses a different contract digest".format(baseline_id))
        rows.append(
            {
                "recordId": baseline_id,
                "algorithm": record.get("algorithm"),
                "implementationVersion": record.get("implementation_version"),
                "contractDigest": record.get("contract_digest"),
                "contractMatches": digest_matches,
                "missingFields": missing,
            }
        )
    return {
        "tool": "list_baselines",
        "status": "pass" if not findings else "incomplete_or_mismatched",
        "provenance": provenance,
        "baselines": rows,
        "findings": findings,
        "limitations": [
            "Listing baseline manifests does not establish that the implementations are strong, tuned, or relevant."
        ],
    }


def read_experiment_manifest(arguments: Mapping[str, Any]) -> JsonObject:
    ensure_arguments(arguments, {"experiment_id"})
    record, provenance = read_record("experiment", arguments.get("experiment_id"))
    evidence_type = record.get("evidence_type")
    findings = []
    if evidence_type not in EVIDENCE_TYPES:
        findings.append("evidence_type is missing or unsupported")
    required = set(EXPERIMENT_FIELDS)
    if evidence_type == "physical_quantum_hardware":
        required |= HARDWARE_FIELDS
    missing = missing_fields(record, required)
    if missing:
        findings.append("missing required fields: " + ", ".join(missing))
    return {
        "tool": "read_experiment_manifest",
        "status": "pass" if not findings else "incomplete",
        "provenance": [provenance],
        "evidenceType": evidence_type,
        "requiredFields": sorted(required),
        "missingFields": missing,
        "record": record,
        "findings": findings,
        "limitations": [
            "Manifest field presence does not authenticate a run, reproduce a result, or prove a scientific claim."
        ],
    }


def contract_digest_for(kind: str, record: Mapping[str, Any], provenance: Mapping[str, Any]) -> Any:
    if kind == "contract":
        return provenance["sha256"]
    return record.get("contract_digest")


def compare_contract_digests(arguments: Mapping[str, Any]) -> JsonObject:
    ensure_arguments(arguments, {"record_refs"})
    refs = arguments.get("record_refs")
    if not isinstance(refs, list) or not 2 <= len(refs) <= MAX_RECORDS_PER_CALL:
        raise EvidenceReadError(
            "record_refs must contain between 2 and {} references".format(
                MAX_RECORDS_PER_CALL
            )
        )
    rows = []
    provenance = []
    for index, ref in enumerate(refs):
        if not isinstance(ref, dict) or set(ref) != {"kind", "record_id"}:
            raise EvidenceReadError(
                "record reference {} must contain only kind and record_id".format(index)
            )
        kind = ref["kind"]
        if kind not in {"contract", "baseline", "experiment"}:
            raise EvidenceReadError("record reference kind must be contract, baseline, or experiment")
        record, source = read_record(kind, ref["record_id"])
        provenance.append(source)
        rows.append(
            {
                "kind": kind,
                "recordId": source["recordId"],
                "contractDigest": contract_digest_for(kind, record, source),
            }
        )
    digests = {row["contractDigest"] for row in rows}
    missing = any(row["contractDigest"] is None for row in rows)
    matches = not missing and len(digests) == 1
    return {
        "tool": "compare_contract_digests",
        "status": "match" if matches else "mismatch_or_missing",
        "provenance": provenance,
        "records": rows,
        "allMatch": matches,
        "findings": (
            []
            if matches
            else ["all compared records must name the same non-missing contract digest"]
        ),
        "limitations": [
            "Equal digests establish record identity, not fair tuning, complete accounting, or equal output quality."
        ],
    }


def list_missing_evidence(arguments: Mapping[str, Any]) -> JsonObject:
    ensure_arguments(arguments, {"gate_id"})
    record, provenance = read_record("gate", arguments.get("gate_id"))
    action = record.get("action")
    if action not in DECISION_REQUIREMENTS:
        raise EvidenceReadError("gate action is missing or unsupported")
    supplied = record.get("supplied_evidence")
    if not isinstance(supplied, list) or not all(
        isinstance(item, str) and item for item in supplied
    ):
        raise EvidenceReadError("supplied_evidence must be an array of strings")
    required = DECISION_REQUIREMENTS[action]
    missing = sorted(required - set(supplied))
    return {
        "tool": "list_missing_evidence",
        "status": "eligible_by_declared_fields" if not missing else "insufficient",
        "provenance": [provenance],
        "requestedAction": action,
        "requiredEvidence": sorted(required),
        "suppliedEvidence": supplied,
        "missingEvidence": missing,
        "limitations": [
            "Eligibility by field presence is not approval and does not validate the truth or quality of supplied evidence."
        ],
    }


def topological_order(items: Sequence[Mapping[str, Any]]) -> List[str]:
    ids = {item["artifact_id"] for item in items}
    dependencies = {
        item["artifact_id"]: set(item.get("depends_on", [])) for item in items
    }
    unresolved = sorted(
        dep for values in dependencies.values() for dep in values if dep not in ids
    )
    if unresolved:
        raise EvidenceReadError(
            "ledger contains unresolved dependencies: " + ", ".join(sorted(set(unresolved)))
        )
    order: List[str] = []
    remaining = dict(dependencies)
    while remaining:
        ready = sorted(key for key, values in remaining.items() if not values)
        if not ready:
            raise EvidenceReadError("ledger dependency graph contains a cycle")
        for key in ready:
            order.append(key)
            remaining.pop(key)
        for values in remaining.values():
            values.difference_update(ready)
    return order


def render_evidence_ledger(arguments: Mapping[str, Any]) -> JsonObject:
    ensure_arguments(arguments, {"ledger_id"})
    ledger, ledger_source = read_record("ledger", arguments.get("ledger_id"))
    artifacts = ledger.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise EvidenceReadError("ledger artifacts must be a non-empty array")
    if len(artifacts) > MAX_RECORDS_PER_CALL:
        raise EvidenceReadError("ledger exceeds the per-call artifact limit")
    normalized = []
    artifact_sources = []
    seen_ids = set()
    for index, item in enumerate(artifacts):
        if not isinstance(item, dict) or set(item) != {
            "artifact_id",
            "kind",
            "record_id",
            "depends_on",
        }:
            raise EvidenceReadError(
                "artifact {} must contain artifact_id, kind, record_id, and depends_on".format(
                    index
                )
            )
        artifact_id = validate_record_id(item["artifact_id"])
        if artifact_id in seen_ids:
            raise EvidenceReadError("ledger artifact identifiers must be unique")
        seen_ids.add(artifact_id)
        kind = item["kind"]
        if kind not in {"contract", "baseline", "experiment", "gate"}:
            raise EvidenceReadError("ledger artifact kind is unsupported")
        dependencies = item["depends_on"]
        if not isinstance(dependencies, list) or not all(
            isinstance(value, str) for value in dependencies
        ):
            raise EvidenceReadError("depends_on must be an array of artifact identifiers")
        _, source = read_record(kind, item["record_id"])
        artifact_sources.append(source)
        normalized.append(
            {
                "artifact_id": artifact_id,
                "kind": kind,
                "record_id": source["recordId"],
                "depends_on": dependencies,
            }
        )
    order = topological_order(normalized)
    by_id = {item["artifact_id"]: item for item in normalized}
    lines = [
        "{}. {} [{}:{}] <- {}".format(
            index + 1,
            artifact_id,
            by_id[artifact_id]["kind"],
            by_id[artifact_id]["record_id"],
            ", ".join(by_id[artifact_id]["depends_on"]) or "root",
        )
        for index, artifact_id in enumerate(order)
    ]
    canonical = json.dumps(
        {"order": order, "artifacts": normalized},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "tool": "render_evidence_ledger",
        "status": "rendered_without_writes",
        "provenance": [ledger_source] + artifact_sources,
        "ledgerId": ledger_source["recordId"],
        "topologicalOrder": order,
        "report": "\n".join(lines),
        "manifestSha256": hashlib.sha256(canonical).hexdigest(),
        "limitations": [
            "The report preserves declared dependencies; it does not authenticate records or approve a decision."
        ],
    }


HANDLERS: Mapping[str, Callable[[Mapping[str, Any]], JsonObject]] = {
    "read_problem_contract": read_problem_contract,
    "list_baselines": list_baselines,
    "read_experiment_manifest": read_experiment_manifest,
    "compare_contract_digests": compare_contract_digests,
    "list_missing_evidence": list_missing_evidence,
    "render_evidence_ledger": render_evidence_ledger,
}

INPUT_SCHEMAS: Mapping[str, JsonObject] = {
    "read_problem_contract": {
        "properties": {"contract_id": {"type": "string"}},
        "required": ["contract_id"],
    },
    "list_baselines": {
        "properties": {
            "baseline_ids": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": MAX_RECORDS_PER_CALL,
            },
            "contract_digest": {"type": "string"},
        },
        "required": ["baseline_ids"],
    },
    "read_experiment_manifest": {
        "properties": {"experiment_id": {"type": "string"}},
        "required": ["experiment_id"],
    },
    "compare_contract_digests": {
        "properties": {
            "record_refs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "kind": {
                            "type": "string",
                            "enum": ["contract", "baseline", "experiment"],
                        },
                        "record_id": {"type": "string"},
                    },
                    "required": ["kind", "record_id"],
                    "additionalProperties": False,
                },
                "minItems": 2,
                "maxItems": MAX_RECORDS_PER_CALL,
            }
        },
        "required": ["record_refs"],
    },
    "list_missing_evidence": {
        "properties": {"gate_id": {"type": "string"}},
        "required": ["gate_id"],
    },
    "render_evidence_ledger": {
        "properties": {"ledger_id": {"type": "string"}},
        "required": ["ledger_id"],
    },
}

DESCRIPTIONS = {
    "read_problem_contract": "Read one local problem contract and report missing task, acceptance, resource, and user fields.",
    "list_baselines": "Read named local classical baseline manifests and compare their declared task-contract identity.",
    "read_experiment_manifest": "Read one local experiment manifest and validate its evidence type and provenance fields.",
    "compare_contract_digests": "Compare exact local contract, baseline, and experiment records for task-contract identity.",
    "list_missing_evidence": "Apply one declared decision gate to a local evidence inventory without filling absent fields.",
    "render_evidence_ledger": "Return a topologically ordered human-readable dependency report without writing files.",
}


def tool_definition(name: str) -> JsonObject:
    schema = {"type": "object", **INPUT_SCHEMAS[name], "additionalProperties": False}
    return {
        "name": name,
        "title": name.replace("_", " ").title(),
        "description": DESCRIPTIONS[name],
        "inputSchema": schema,
        "outputSchema": {"type": "object"},
        "annotations": {
            "title": name.replace("_", " ").title(),
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    }


def tool_result(name: str, arguments: Mapping[str, Any]) -> JsonObject:
    try:
        payload = HANDLERS[name](arguments)
    except EvidenceReadError as exc:
        return {"content": [{"type": "text", "text": str(exc)}], "isError": True}
    return {
        "content": [
            {"type": "text", "text": json.dumps(payload, indent=2, sort_keys=True)}
        ],
        "structuredContent": payload,
        "isError": False,
    }


def success(request_id: JsonValue, result: JsonObject) -> JsonObject:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error(request_id: JsonValue, code: int, message: str) -> JsonObject:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def handle_request(message: Any) -> Optional[JsonObject]:
    if not isinstance(message, dict):
        return error(None, -32600, "Invalid Request")
    request_id = message.get("id")
    is_notification = "id" not in message
    if message.get("jsonrpc") != "2.0" or not isinstance(
        message.get("method"), str
    ):
        return None if is_notification else error(request_id, -32600, "Invalid Request")
    method = message["method"]
    params = message.get("params", {})
    if is_notification:
        return None
    if method == "initialize":
        requested = params.get("protocolVersion") if isinstance(params, dict) else None
        negotiated = (
            requested
            if requested in SUPPORTED_PROTOCOL_VERSIONS
            else LATEST_PROTOCOL_VERSION
        )
        return success(
            request_id,
            {
                "protocolVersion": negotiated,
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": SERVER_NAME,
                    "title": "QuantumGridOS Advantage Evidence",
                    "version": SERVER_VERSION,
                },
                "instructions": (
                    "Read exact local evidence records only. Preserve missing fields and "
                    "evidence types. Do not execute benchmarks, contact providers, write files, "
                    "or treat schema validity as proof of a scientific conclusion."
                ),
            },
        )
    if method == "ping":
        return success(request_id, {})
    if method == "tools/list":
        return success(
            request_id,
            {"tools": [tool_definition(name) for name in HANDLERS]},
        )
    if method == "tools/call":
        if not isinstance(params, dict):
            return error(request_id, -32602, "tools/call params must be an object")
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or name not in HANDLERS:
            return error(request_id, -32602, "Unknown tool")
        if not isinstance(arguments, dict):
            return error(request_id, -32602, "tool arguments must be an object")
        return success(request_id, tool_result(name, arguments))
    return error(request_id, -32601, "Method not found")


def process_payload(
    payload: Any,
) -> Optional[Union[JsonObject, List[JsonObject]]]:
    if isinstance(payload, list):
        if not payload:
            return error(None, -32600, "Invalid Request")
        responses = [
            response
            for item in payload
            if (response := handle_request(item)) is not None
        ]
        return responses or None
    return handle_request(payload)


def write_message(message: Union[JsonObject, List[JsonObject]]) -> None:
    sys.stdout.write(
        json.dumps(message, separators=(",", ":"), ensure_ascii=False) + "\n"
    )
    sys.stdout.flush()


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            write_message(error(None, -32700, "Parse error"))
            continue
        try:
            response = process_payload(payload)
        except Exception as exc:
            print("internal MCP error: {}".format(type(exc).__name__), file=sys.stderr)
            response = error(None, -32603, "Internal error")
        if response is not None:
            write_message(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
