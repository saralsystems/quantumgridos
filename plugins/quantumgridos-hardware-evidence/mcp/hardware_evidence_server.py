#!/usr/bin/env python3
"""Dependency-free, read-only MCP server for quantum hardware evidence records."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union


SERVER_NAME = "quantumgridos-hardware-evidence"
SERVER_VERSION = "0.1.0"
LATEST_PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOL_VERSIONS = {
    "2024-11-05",
    "2025-03-26",
    "2025-06-18",
    "2025-11-25",
}
RECORDS_ENV = "QUANTUMGRIDOS_HARDWARE_EVIDENCE_DIR"
DEFAULT_RECORDS_ROOT = Path(__file__).resolve().parent.parent / "records"
MAX_RECORD_BYTES = 1024 * 1024
RECORD_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

JsonObject = Dict[str, Any]
JsonValue = Union[None, bool, int, float, str, List[Any], JsonObject]


@dataclass(frozen=True)
class RecordTool:
    name: str
    title: str
    description: str
    directory: str
    kind: str
    validator: bool = False


RECORD_TOOLS: Sequence[RecordTool] = (
    RecordTool(
        "get_experiment_intent",
        "Get experiment intent",
        "Read one local logical experiment and measurement-contract record.",
        "intents",
        "intent",
    ),
    RecordTool(
        "get_backend_capability_snapshot",
        "Get backend capability snapshot",
        "Read one local timestamped target and backend-capability snapshot.",
        "capabilities",
        "capability",
    ),
    RecordTool(
        "validate_compilation_record",
        "Validate compilation record",
        "Read one local compilation record and validate its referenced intent, target, operations, connectivity, layouts, and measurement map.",
        "compilations",
        "compilation",
        True,
    ),
    RecordTool(
        "get_execution_record",
        "Get execution record",
        "Read one local simulator or provider execution-provenance record.",
        "executions",
        "execution",
    ),
    RecordTool(
        "get_evidence_record",
        "Get evidence record",
        "Read one local raw-and-derived evidence record with bounded conclusion.",
        "evidence",
        "evidence",
    ),
)
TOOLS_BY_NAME = {tool.name: tool for tool in RECORD_TOOLS}


class RecordReadError(ValueError):
    """A bounded error safe to return as a tool result."""


def records_root() -> Path:
    configured = os.environ.get(RECORDS_ENV)
    candidate = Path(configured) if configured else DEFAULT_RECORDS_ROOT
    return candidate.resolve(strict=False)


def validate_record_id(value: Any) -> str:
    if not isinstance(value, str) or RECORD_ID_PATTERN.fullmatch(value) is None:
        raise RecordReadError(
            "record_id must start with a letter or digit, contain only letters, digits, "
            "period, underscore, or hyphen, and be at most 128 characters"
        )
    return value


def read_record(directory: str, kind: str, record_id_value: Any) -> JsonObject:
    record_id = validate_record_id(record_id_value)
    root = records_root()
    target = (root / directory / (record_id + ".json")).resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise RecordReadError("record resolves outside the configured records root") from exc
    if not target.is_file():
        raise RecordReadError("record not found: {}/{}.json".format(directory, record_id))
    try:
        if target.stat().st_size > MAX_RECORD_BYTES:
            raise RecordReadError("record exceeds the 1 MiB read limit")
        raw = target.read_bytes()
    except RecordReadError:
        raise
    except OSError as exc:
        raise RecordReadError("record could not be read") from exc
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecordReadError("record is not a valid UTF-8 JSON document") from exc
    if not isinstance(parsed, dict):
        raise RecordReadError("record must contain one JSON object")
    if parsed.get("record_id") != record_id:
        raise RecordReadError("record_id inside the document does not match the requested identifier")
    return {
        "recordKind": kind,
        "recordId": record_id,
        "sourcePath": "{}/{}.json".format(directory, record_id),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "record": parsed,
    }


def validate_compilation(payload: JsonObject) -> JsonObject:
    compilation = payload["record"]
    passed: List[str] = []
    failed: List[str] = []
    unknown: List[str] = []
    references: JsonObject = {}

    try:
        intent = read_record("intents", "intent", compilation.get("intent_record_id"))
        references["intent"] = {
            "recordId": intent["recordId"],
            "sha256": intent["sha256"],
        }
    except RecordReadError as exc:
        intent = None
        failed.append("intent reference: " + str(exc))

    try:
        capability = read_record(
            "capabilities", "capability", compilation.get("capability_record_id")
        )
        references["capability"] = {
            "recordId": capability["recordId"],
            "sha256": capability["sha256"],
        }
    except RecordReadError as exc:
        capability = None
        failed.append("capability reference: " + str(exc))

    if intent is not None:
        expected = intent["record"].get("circuit_sha256")
        actual = compilation.get("source_circuit_sha256")
        if isinstance(expected, str) and isinstance(actual, str):
            if expected == actual:
                passed.append("source circuit hash matches intent")
            else:
                failed.append("source circuit hash does not match intent")
        else:
            unknown.append("source circuit hash comparison")

    physical_qubits = set()
    supported_operations = set()
    coupling_edges = set()
    if capability is not None:
        target = capability["record"]
        expected = target.get("target_sha256")
        actual = compilation.get("target_sha256")
        if isinstance(expected, str) and isinstance(actual, str):
            if expected == actual:
                passed.append("target hash matches capability snapshot")
            else:
                failed.append("target hash does not match capability snapshot")
        else:
            unknown.append("target hash comparison")
        physical_values = target.get("physical_qubits")
        operation_values = target.get("supported_operations")
        edge_values = target.get("coupling_edges")
        physical_qubits = set(physical_values) if isinstance(physical_values, list) else set()
        supported_operations = set(operation_values) if isinstance(operation_values, list) else set()
        coupling_edges = {
            tuple(edge)
            for edge in edge_values if isinstance(edge, list) and len(edge) == 2
        } if isinstance(edge_values, list) else set()

    operations = compilation.get("isa_operations")
    if isinstance(operations, list) and capability is not None:
        for index, operation in enumerate(operations):
            if not isinstance(operation, dict):
                failed.append("ISA operation {} is not an object".format(index))
                continue
            name = operation.get("name")
            qubits = operation.get("qubits")
            if name not in supported_operations:
                failed.append("unsupported operation {} at index {}".format(name, index))
            if (
                not isinstance(qubits, list)
                or any(not isinstance(qubit, int) for qubit in qubits)
                or any(qubit not in physical_qubits for qubit in qubits)
            ):
                failed.append("invalid physical qubits at operation index {}".format(index))
            elif len(qubits) == 2 and tuple(qubits) not in coupling_edges:
                failed.append("unsupported two-qubit edge {} at index {}".format(qubits, index))
        if not any(item.startswith("unsupported operation") for item in failed):
            passed.append("all ISA operation names are target-supported")
        if not any("physical qubits" in item or "two-qubit edge" in item for item in failed):
            passed.append("all ISA qargs and two-qubit edges are target-supported")
    else:
        unknown.append("ISA operation and connectivity validation")

    logical_qubits = intent["record"].get("logical_qubits") if intent is not None else None
    for field in ("initial_layout", "final_layout"):
        layout = compilation.get(field)
        if capability is None or not isinstance(logical_qubits, int):
            unknown.append(field + " validation")
            continue
        valid = (
            isinstance(layout, list)
            and all(isinstance(position, int) for position in layout)
            and len(layout) == logical_qubits
            and len(set(layout)) == len(layout)
            and set(layout) <= physical_qubits
        )
        if valid:
            passed.append(field + " is a unique in-target placement")
        else:
            failed.append(field + " is not a unique in-target placement")

    final_layout = compilation.get("final_layout")
    measurement_map = compilation.get("measurement_map_classical_to_physical")
    if isinstance(final_layout, list) and isinstance(measurement_map, dict):
        measured_positions = set(measurement_map.values())
        if measured_positions == set(final_layout):
            passed.append("measurement map covers final logical positions")
        else:
            failed.append("measurement map does not cover final logical positions")
    else:
        unknown.append("measurement map consistency")

    return {
        "passed": passed,
        "failed": failed,
        "unknown": unknown,
        "valid": not failed,
        "scope": (
            "Internal consistency of local records only; this does not prove provider "
            "authenticity, physical execution, or compiler correctness for arbitrary inputs."
        ),
        "referencedRecords": references,
    }


def tool_definition(tool: RecordTool) -> JsonObject:
    output_properties: JsonObject = {
        "recordKind": {"type": "string"},
        "recordId": {"type": "string"},
        "sourcePath": {"type": "string"},
        "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
        "record": {"type": "object"},
    }
    required = list(output_properties)
    if tool.validator:
        output_properties["validation"] = {"type": "object"}
        required.append("validation")
    return {
        "name": tool.name,
        "title": tool.title,
        "description": tool.description,
        "inputSchema": {
            "type": "object",
            "properties": {
                "record_id": {
                    "type": "string",
                    "description": "Exact record identifier; this is not a filesystem path.",
                    "minLength": 1,
                    "maxLength": 128,
                    "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$",
                }
            },
            "required": ["record_id"],
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "properties": output_properties,
            "required": required,
            "additionalProperties": False,
        },
        "annotations": {
            "title": tool.title,
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    }


def tool_result(tool: RecordTool, arguments: Mapping[str, Any]) -> JsonObject:
    extra = sorted(set(arguments) - {"record_id"})
    if extra:
        return {"content": [{"type": "text", "text": "unexpected argument(s): " + ", ".join(extra)}], "isError": True}
    try:
        payload = read_record(tool.directory, tool.kind, arguments.get("record_id"))
        if tool.validator:
            payload["validation"] = validate_compilation(payload)
    except RecordReadError as exc:
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
    if is_notification:
        return None
    method = message["method"]
    params = message.get("params", {})
    if method == "initialize":
        requested = params.get("protocolVersion") if isinstance(params, dict) else None
        negotiated = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else LATEST_PROTOCOL_VERSION
        return success(request_id, {
            "protocolVersion": negotiated,
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": SERVER_NAME,
                "title": "QuantumGridOS Hardware Evidence",
                "version": SERVER_VERSION,
                "description": "Read-only access to five local quantum experiment records.",
            },
            "instructions": (
                "Read only exact identifiers. Keep intent, capability, compilation, execution, "
                "and evidence separate. Never infer physical execution from a local record."
            ),
        })
    if method == "ping":
        return success(request_id, {})
    if method == "tools/list":
        return success(request_id, {"tools": [tool_definition(tool) for tool in RECORD_TOOLS]})
    if method == "tools/call":
        if not isinstance(params, dict):
            return error(request_id, -32602, "tools/call params must be an object")
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or name not in TOOLS_BY_NAME:
            return error(request_id, -32602, "Unknown tool")
        if not isinstance(arguments, dict):
            return error(request_id, -32602, "tool arguments must be an object")
        return success(request_id, tool_result(TOOLS_BY_NAME[name], arguments))
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
        except Exception as exc:  # Defensive boundary: never leak a traceback over stdout.
            print("internal MCP error: {}".format(type(exc).__name__), file=sys.stderr)
            response = error(None, -32603, "Internal error")
        if response is not None:
            write_message(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
