#!/usr/bin/env python3
"""Dependency-free, read-only MCP server for QuantumGridOS evidence records."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union


SERVER_NAME = "quantumgridos-records"
SERVER_VERSION = "0.1.0"
LATEST_PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOL_VERSIONS = {
    "2024-11-05",
    "2025-03-26",
    "2025-06-18",
    "2025-11-25",
}
RECORDS_ENV = "QUANTUMGRIDOS_RECORDS_DIR"
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


RECORD_TOOLS: Sequence[RecordTool] = (
    RecordTool(
        "get_request_record",
        "Get request record",
        "Read one local service request record by its exact record identifier.",
        "requests",
        "request",
    ),
    RecordTool(
        "get_execution_plan",
        "Get execution plan",
        "Read one local immutable execution-plan record by its exact record identifier.",
        "plans",
        "plan",
    ),
    RecordTool(
        "get_job_snapshot",
        "Get job snapshot",
        "Read one local service and provider job-state snapshot by its exact record identifier.",
        "jobs",
        "job",
    ),
    RecordTool(
        "get_result_record",
        "Get result record",
        "Read one local raw-and-derived result record by its exact record identifier.",
        "results",
        "result",
    ),
    RecordTool(
        "get_operations_summary",
        "Get operations summary",
        "Read one local operations-evidence summary by its exact record identifier.",
        "operations",
        "operations",
    ),
)
TOOLS_BY_NAME = {tool.name: tool for tool in RECORD_TOOLS}


class RecordReadError(ValueError):
    """A bounded error that is safe to return as a tool result."""


def records_root() -> Path:
    configured = os.environ.get(RECORDS_ENV)
    candidate = Path(configured) if configured else DEFAULT_RECORDS_ROOT
    return candidate.resolve(strict=False)


def tool_definition(tool: RecordTool) -> JsonObject:
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
            "properties": {
                "recordKind": {"type": "string"},
                "recordId": {"type": "string"},
                "sourcePath": {"type": "string"},
                "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                "record": {"type": "object"},
            },
            "required": ["recordKind", "recordId", "sourcePath", "sha256", "record"],
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


def validate_record_id(value: Any) -> str:
    if not isinstance(value, str) or RECORD_ID_PATTERN.fullmatch(value) is None:
        raise RecordReadError(
            "record_id must start with a letter or digit, contain only letters, digits, "
            "period, underscore, or hyphen, and be at most 128 characters"
        )
    return value


def read_record(tool: RecordTool, arguments: Mapping[str, Any]) -> JsonObject:
    extra = sorted(set(arguments) - {"record_id"})
    if extra:
        raise RecordReadError("unexpected argument(s): " + ", ".join(extra))

    record_id = validate_record_id(arguments.get("record_id"))
    root = records_root()
    target = (root / tool.directory / (record_id + ".json")).resolve(strict=False)

    try:
        target.relative_to(root)
    except ValueError as exc:
        raise RecordReadError("record resolves outside the configured records root") from exc

    if not target.is_file():
        raise RecordReadError(
            "record not found: {}/{}.json".format(tool.directory, record_id)
        )

    try:
        if target.stat().st_size > MAX_RECORD_BYTES:
            raise RecordReadError("record exceeds the 1 MiB read limit")
        raw = target.read_bytes()
    except RecordReadError:
        raise
    except OSError as exc:
        raise RecordReadError("record could not be read") from exc
    if len(raw) > MAX_RECORD_BYTES:
        raise RecordReadError("record exceeds the 1 MiB read limit")

    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecordReadError("record is not a valid UTF-8 JSON document") from exc
    if not isinstance(parsed, dict):
        raise RecordReadError("record must contain one JSON object")
    if parsed.get("record_id") != record_id:
        raise RecordReadError("record_id inside the document does not match the requested identifier")

    return {
        "recordKind": tool.kind,
        "recordId": record_id,
        "sourcePath": "{}/{}.json".format(tool.directory, record_id),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "record": parsed,
    }


def tool_result(tool: RecordTool, arguments: Mapping[str, Any]) -> JsonObject:
    try:
        payload = read_record(tool, arguments)
    except RecordReadError as exc:
        return {
            "content": [{"type": "text", "text": str(exc)}],
            "isError": True,
        }
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, indent=2, sort_keys=True),
            }
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
    if message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
        return None if is_notification else error(request_id, -32600, "Invalid Request")

    method = message["method"]
    params = message.get("params", {})
    if is_notification:
        return None

    if method == "initialize":
        requested = params.get("protocolVersion") if isinstance(params, dict) else None
        negotiated = (
            requested if requested in SUPPORTED_PROTOCOL_VERSIONS else LATEST_PROTOCOL_VERSION
        )
        return success(
            request_id,
            {
                "protocolVersion": negotiated,
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": SERVER_NAME,
                    "title": "QuantumGridOS Records",
                    "version": SERVER_VERSION,
                    "description": "Read-only access to five local quantum-service evidence records.",
                },
                "instructions": (
                    "Read only exact record identifiers supplied by the user. Keep request, plan, "
                    "job, result, and operations records separate. Never infer hardware execution "
                    "or scientific validity from the presence of a record."
                ),
            },
        )

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
