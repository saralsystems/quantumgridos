#!/usr/bin/env python3
"""Dependency-free, read-only MCP server for local QEC evidence records."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Union


SERVER_NAME = "quantumgridos-qec-evidence"
SERVER_VERSION = "0.1.0"
LATEST_PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOL_VERSIONS = {
    "2024-11-05",
    "2025-03-26",
    "2025-06-18",
    "2025-11-25",
}
EVIDENCE_ENV = "QUANTUMGRIDOS_QEC_EVIDENCE_DIR"
DEFAULT_EVIDENCE_ROOT = Path(__file__).resolve().parent.parent / "records"
MAX_RECORD_BYTES = 1024 * 1024
RECORD_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
PAULI_PATTERN = re.compile(r"^[IXYZ]+$")

JsonObject = Dict[str, Any]
JsonValue = Union[None, bool, int, float, str, List[Any], JsonObject]

KIND_DIRECTORIES = {
    "code": "codes",
    "syndrome": "syndromes",
    "run": "runs",
    "claim": "claims",
    "bundle": "bundles",
}

EVIDENCE_REQUIREMENTS = {
    "syndrome_detection": {"code", "circuit", "raw_syndrome"},
    "corrected_observable": {"code", "circuit", "raw_syndrome", "decoder", "result", "comparator"},
    "break_even_memory": {"code", "circuit", "raw_syndrome", "decoder", "result", "comparator", "uncertainty"},
    "repeated_protection": {"code", "circuit", "raw_syndrome", "decoder", "result", "rounds", "uncertainty"},
    "below_threshold_scaling": {"code", "circuit", "raw_syndrome", "decoder", "result", "distances", "comparator", "uncertainty"},
    "fault_tolerant_operations": {"code", "fault_tolerant_circuit", "raw_syndrome", "decoder", "logical_operation", "result", "uncertainty"},
    "validated_logical_algorithm": {"code", "fault_tolerant_circuit", "decoder", "logical_algorithm", "failure_budget", "result", "uncertainty"},
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
        raise EvidenceReadError("record_id inside the document does not match the requested identifier")
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


def pauli_anticommutes(left: str, right: str) -> bool:
    disagreements = sum(
        a != "I" and b != "I" and a != b for a, b in zip(left, right)
    )
    return bool(disagreements % 2)


def symplectic_row(pauli: str) -> List[int]:
    x = [int(symbol in "XY") for symbol in pauli]
    z = [int(symbol in "ZY") for symbol in pauli]
    return x + z


def gf2_rank(rows: Sequence[Sequence[int]]) -> int:
    matrix = [list(row) for row in rows]
    if not matrix:
        return 0
    rank = 0
    for column in range(len(matrix[0])):
        pivot = next((index for index in range(rank, len(matrix)) if matrix[index][column]), None)
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        for index in range(len(matrix)):
            if index != rank and matrix[index][column]:
                matrix[index] = [a ^ b for a, b in zip(matrix[index], matrix[rank])]
        rank += 1
    return rank


def inspect_code_spec(arguments: Mapping[str, Any]) -> JsonObject:
    ensure_arguments(arguments, {"code_id"})
    record, provenance = read_record("code", arguments.get("code_id"))
    findings: List[str] = []
    n, k, declared_distance = record.get("n"), record.get("k"), record.get("distance")
    generators = record.get("stabilizer_generators")
    if not isinstance(n, int) or not isinstance(k, int) or not (n > k >= 0):
        findings.append("n and k must be integers satisfying n > k >= 0")
    if not isinstance(declared_distance, int) or declared_distance < 1:
        findings.append("distance must be a positive integer")
    valid_generators = (
        isinstance(n, int)
        and isinstance(generators, list)
        and all(isinstance(item, str) and len(item) == n and PAULI_PATTERN.fullmatch(item) for item in generators)
    )
    rank: Optional[int] = None
    if not valid_generators:
        findings.append("every stabilizer generator must be an n-character I/X/Y/Z string")
    else:
        noncommuting = [
            [i, j]
            for i in range(len(generators))
            for j in range(i + 1, len(generators))
            if pauli_anticommutes(generators[i], generators[j])
        ]
        if noncommuting:
            findings.append("stabilizer generators do not commute at pairs {}".format(noncommuting))
        rank = gf2_rank([symplectic_row(item) for item in generators])
        if isinstance(n, int) and isinstance(k, int) and rank != n - k:
            findings.append("independent-generator rank {} does not equal n-k {}".format(rank, n - k))
    return {
        "tool": "inspect_code_spec",
        "status": "pass" if not findings else "fail",
        "provenance": [provenance],
        "declared": {"n": n, "k": k, "distance": declared_distance},
        "computedGeneratorRank": rank,
        "findings": findings,
        "limitations": ["The declared distance is not proven by these structural checks."],
    }


def validate_syndrome_schema(arguments: Mapping[str, Any]) -> JsonObject:
    ensure_arguments(arguments, {"syndrome_id"})
    record, provenance = read_record("syndrome", arguments.get("syndrome_id"))
    entries = record.get("records")
    findings: List[str] = []
    required = {"round", "check_id", "ancilla", "basis", "bit", "timestamp", "provenance"}
    seen: set[tuple[Any, Any]] = set()
    if not isinstance(entries, list) or not entries:
        findings.append("records must be a non-empty array")
        entries = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            findings.append("record {} must be an object".format(index))
            continue
        missing = sorted(required - set(entry))
        if missing:
            findings.append("record {} is missing {}".format(index, ", ".join(missing)))
        if entry.get("basis") not in {"X", "Z"}:
            findings.append("record {} basis must be X or Z".format(index))
        if entry.get("bit") not in {0, 1}:
            findings.append("record {} bit must be 0 or 1".format(index))
        key = (entry.get("round"), entry.get("check_id"))
        if key in seen:
            findings.append("duplicate round/check pair at record {}".format(index))
        seen.add(key)
    return {
        "tool": "validate_syndrome_schema",
        "status": "pass" if not findings else "fail",
        "provenance": [provenance],
        "recordCount": len(entries),
        "findings": findings,
        "limitations": ["Schema validity does not prove that measurements came from hardware or that the check circuit was correct."],
    }


def compare_distance_runs(arguments: Mapping[str, Any]) -> JsonObject:
    ensure_arguments(arguments, {"run_ids"})
    run_ids = arguments.get("run_ids")
    if not isinstance(run_ids, list) or not 2 <= len(run_ids) <= 16:
        raise EvidenceReadError("run_ids must contain between 2 and 16 exact identifiers")
    if len(set(run_ids)) != len(run_ids):
        raise EvidenceReadError("run_ids must be unique")
    pairs = [read_record("run", item) for item in run_ids]
    records = [pair[0] for pair in pairs]
    provenance = [pair[1] for pair in pairs]
    compatibility_fields = ("code_family", "circuit_family", "decoder_version", "task", "statistics_method")
    findings: List[str] = []
    for field in compatibility_fields:
        values = {json.dumps(record.get(field), sort_keys=True) for record in records}
        if len(values) != 1 or "null" in values:
            findings.append("incompatible or missing {}".format(field))
    distances = [record.get("distance") for record in records]
    if not all(isinstance(value, int) and value > 0 for value in distances):
        findings.append("every run needs a positive integer distance")
    elif len(set(distances)) != len(distances):
        findings.append("distances must be distinct")
    rates = [record.get("logical_error_rate") for record in records]
    if not all(isinstance(value, (int, float)) and 0 <= value <= 1 for value in rates):
        findings.append("every run needs a logical_error_rate between 0 and 1")
    if not all(record.get("uncertainty") is not None for record in records):
        findings.append("every run needs uncertainty metadata")
    ordered = sorted(
        ({"recordId": record["record_id"], "distance": record.get("distance"), "logicalErrorRate": record.get("logical_error_rate")} for record in records),
        key=lambda item: item["distance"] if isinstance(item["distance"], int) else -1,
    )
    decreasing = bool(not findings and all(ordered[i]["logicalErrorRate"] > ordered[i + 1]["logicalErrorRate"] for i in range(len(ordered) - 1)))
    return {
        "tool": "compare_distance_runs",
        "status": "compatible" if not findings else "incompatible",
        "provenance": provenance,
        "runs": ordered,
        "logicalErrorDecreasesWithDistance": decreasing,
        "findings": findings,
        "boundedConclusion": (
            "The supplied compatible point estimates decrease with distance; a threshold claim still requires the declared uncertainty and protocol analysis."
            if decreasing
            else "The supplied records do not establish decreasing logical error across compatible distances."
        ),
    }


def audit_fault_tolerance_claim(arguments: Mapping[str, Any]) -> JsonObject:
    ensure_arguments(arguments, {"claim_id"})
    record, provenance = read_record("claim", arguments.get("claim_id"))
    rung = record.get("evidence_rung")
    supplied = record.get("supplied_evidence", [])
    if rung not in EVIDENCE_REQUIREMENTS:
        raise EvidenceReadError("evidence_rung is missing or unsupported")
    if not isinstance(supplied, list) or not all(isinstance(item, str) for item in supplied):
        raise EvidenceReadError("supplied_evidence must be an array of strings")
    required = EVIDENCE_REQUIREMENTS[rung]
    missing = sorted(required - set(supplied))
    warnings = []
    if record.get("postselected") is True:
        warnings.append("postselection must be reported with acceptance probability and resource cost")
    if record.get("decoder_information_boundary") == "offline_future_aware":
        warnings.append("offline future-aware decoding must not be described as causal or real-time")
    return {
        "tool": "audit_fault_tolerance_claim",
        "status": "supported_by_supplied_fields" if not missing else "insufficient",
        "provenance": [provenance],
        "proposedClaim": record.get("proposed_claim"),
        "requestedRung": rung,
        "requiredEvidence": sorted(required),
        "missingEvidence": missing,
        "warnings": warnings,
        "limitations": ["Field presence does not authenticate an artifact or independently validate a scientific conclusion."],
    }


def export_qec_evidence_bundle(arguments: Mapping[str, Any]) -> JsonObject:
    ensure_arguments(arguments, {"bundle_id"})
    bundle, bundle_provenance = read_record("bundle", arguments.get("bundle_id"))
    artifacts = bundle.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise EvidenceReadError("bundle artifacts must be a non-empty array")
    exported = []
    for index, item in enumerate(artifacts):
        if not isinstance(item, dict) or set(item) != {"kind", "record_id"}:
            raise EvidenceReadError("artifact {} must contain only kind and record_id".format(index))
        kind = item["kind"]
        if kind == "bundle":
            raise EvidenceReadError("nested bundles are not supported")
        _, provenance = read_record(kind, item["record_id"])
        exported.append(provenance)
    canonical = json.dumps(exported, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "tool": "export_qec_evidence_bundle",
        "status": "returned_without_writes",
        "provenance": [bundle_provenance] + exported,
        "bundleId": bundle["record_id"],
        "artifactCount": len(exported),
        "manifestSha256": hashlib.sha256(canonical).hexdigest(),
        "limitations": ["This tool returns a digest manifest; it does not copy files, contact providers, or authenticate scientific claims."],
    }


HANDLERS: Mapping[str, Callable[[Mapping[str, Any]], JsonObject]] = {
    "inspect_code_spec": inspect_code_spec,
    "validate_syndrome_schema": validate_syndrome_schema,
    "compare_distance_runs": compare_distance_runs,
    "audit_fault_tolerance_claim": audit_fault_tolerance_claim,
    "export_qec_evidence_bundle": export_qec_evidence_bundle,
}

INPUT_SCHEMAS: Mapping[str, JsonObject] = {
    "inspect_code_spec": {"properties": {"code_id": {"type": "string"}}, "required": ["code_id"]},
    "validate_syndrome_schema": {"properties": {"syndrome_id": {"type": "string"}}, "required": ["syndrome_id"]},
    "compare_distance_runs": {"properties": {"run_ids": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 16}}, "required": ["run_ids"]},
    "audit_fault_tolerance_claim": {"properties": {"claim_id": {"type": "string"}}, "required": ["claim_id"]},
    "export_qec_evidence_bundle": {"properties": {"bundle_id": {"type": "string"}}, "required": ["bundle_id"]},
}

DESCRIPTIONS = {
    "inspect_code_spec": "Read one local code specification and check generator form, commutation, and independent rank.",
    "validate_syndrome_schema": "Read one local syndrome batch and validate raw round, check, ancilla, basis, bit, timestamp, and provenance fields.",
    "compare_distance_runs": "Compare named local distance-run records only when their circuit, decoder, task, and statistical contracts match.",
    "audit_fault_tolerance_claim": "Map one local proposed QEC claim to an evidence rung and report missing requirements.",
    "export_qec_evidence_bundle": "Return a digest manifest for named immutable local evidence records without writing or contacting a provider.",
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
        "content": [{"type": "text", "text": json.dumps(payload, indent=2, sort_keys=True)}],
        "structuredContent": payload,
        "isError": False,
    }


def success(request_id: JsonValue, result: JsonObject) -> JsonObject:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error(request_id: JsonValue, code: int, message: str) -> JsonObject:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_request(message: Any) -> Optional[JsonObject]:
    if not isinstance(message, dict):
        return error(None, -32600, "Invalid Request")
    request_id = message.get("id")
    is_notification = "id" not in message
    if message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
        return None if is_notification else error(request_id, -32600, "Invalid Request")
    method, params = message["method"], message.get("params", {})
    if is_notification:
        return None
    if method == "initialize":
        requested = params.get("protocolVersion") if isinstance(params, dict) else None
        negotiated = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else LATEST_PROTOCOL_VERSION
        return success(request_id, {
            "protocolVersion": negotiated,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "title": "QuantumGridOS QEC Evidence", "version": SERVER_VERSION},
            "instructions": "Read only exact local record identifiers. Preserve unknowns. Never infer hardware execution or submit, modify, or correct a provider system.",
        })
    if method == "ping":
        return success(request_id, {})
    if method == "tools/list":
        return success(request_id, {"tools": [tool_definition(name) for name in HANDLERS]})
    if method == "tools/call":
        if not isinstance(params, dict):
            return error(request_id, -32602, "tools/call params must be an object")
        name, arguments = params.get("name"), params.get("arguments", {})
        if not isinstance(name, str) or name not in HANDLERS:
            return error(request_id, -32602, "Unknown tool")
        if not isinstance(arguments, dict):
            return error(request_id, -32602, "tool arguments must be an object")
        return success(request_id, tool_result(name, arguments))
    return error(request_id, -32601, "Method not found")


def process_payload(payload: Any) -> Optional[Union[JsonObject, List[JsonObject]]]:
    if isinstance(payload, list):
        if not payload:
            return error(None, -32600, "Invalid Request")
        responses = [response for item in payload if (response := handle_request(item)) is not None]
        return responses or None
    return handle_request(payload)


def write_message(message: Union[JsonObject, List[JsonObject]]) -> None:
    sys.stdout.write(json.dumps(message, separators=(",", ":"), ensure_ascii=False) + "\n")
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
