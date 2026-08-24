"""Protocol, validation, and packaging tests for the hardware-evidence plugin."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PLUGIN_ROOT.parent.parent
SERVER_PATH = PLUGIN_ROOT / "mcp" / "hardware_evidence_server.py"
SPEC = importlib.util.spec_from_file_location("quantumgridos_hardware_evidence_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
SERVER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SERVER
SPEC.loader.exec_module(SERVER)


class HardwareEvidenceServerTests(unittest.TestCase):
    def test_lists_five_read_only_closed_world_tools(self) -> None:
        response = SERVER.handle_request(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        tools = response["result"]["tools"]
        self.assertEqual(
            [tool["name"] for tool in tools],
            [
                "get_experiment_intent",
                "get_backend_capability_snapshot",
                "validate_compilation_record",
                "get_execution_record",
                "get_evidence_record",
            ],
        )
        for tool in tools:
            self.assertTrue(tool["annotations"]["readOnlyHint"])
            self.assertFalse(tool["annotations"]["destructiveHint"])
            self.assertFalse(tool["annotations"]["openWorldHint"])

    def test_packaged_compilation_fixture_passes_internal_validation(self) -> None:
        result = SERVER.tool_result(
            SERVER.TOOLS_BY_NAME["validate_compilation_record"],
            {"record_id": "demo-compilation-001"},
        )
        self.assertFalse(result["isError"])
        payload = result["structuredContent"]
        self.assertTrue(payload["validation"]["valid"])
        self.assertEqual(payload["validation"]["failed"], [])
        self.assertEqual(
            set(payload["validation"]["referencedRecords"]),
            {"intent", "capability"},
        )

    def test_validator_detects_unsupported_operation_and_edge(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ("intents", "capabilities", "compilations"):
                (root / directory).mkdir()
            (root / "intents" / "intent.json").write_text(
                json.dumps({"record_id": "intent", "circuit_sha256": "a", "logical_qubits": 2}),
                encoding="utf-8",
            )
            (root / "capabilities" / "capability.json").write_text(
                json.dumps({
                    "record_id": "capability",
                    "target_sha256": "b",
                    "physical_qubits": [0, 1, 2],
                    "supported_operations": ["rz", "cz", "measure"],
                    "coupling_edges": [[0, 1], [1, 0]],
                }),
                encoding="utf-8",
            )
            (root / "compilations" / "bad.json").write_text(
                json.dumps({
                    "record_id": "bad",
                    "intent_record_id": "intent",
                    "capability_record_id": "capability",
                    "source_circuit_sha256": "a",
                    "target_sha256": "b",
                    "initial_layout": [0, 2],
                    "final_layout": [0, 1],
                    "measurement_map_classical_to_physical": {"0": 0, "1": 1},
                    "isa_operations": [
                        {"name": "cx", "qubits": [0, 2]},
                        {"name": "measure", "qubits": [0]},
                    ],
                }),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {SERVER.RECORDS_ENV: str(root)}):
                result = SERVER.tool_result(
                    SERVER.TOOLS_BY_NAME["validate_compilation_record"],
                    {"record_id": "bad"},
                )
        validation = result["structuredContent"]["validation"]
        self.assertFalse(validation["valid"])
        self.assertTrue(any("unsupported operation" in item for item in validation["failed"]))
        self.assertTrue(any("two-qubit edge" in item for item in validation["failed"]))

    def test_rejects_traversal_unknown_arguments_and_record_id_mismatch(self) -> None:
        tool = SERVER.TOOLS_BY_NAME["get_evidence_record"]
        self.assertTrue(SERVER.tool_result(tool, {"record_id": "../secret"})["isError"])
        self.assertTrue(SERVER.tool_result(tool, {"record_id": "safe", "path": "/tmp"})["isError"])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / "evidence"
            directory.mkdir()
            (directory / "one.json").write_text(
                json.dumps({"record_id": "two"}), encoding="utf-8"
            )
            with patch.dict(os.environ, {SERVER.RECORDS_ENV: str(root)}):
                result = SERVER.tool_result(tool, {"record_id": "one"})
        self.assertTrue(result["isError"])
        self.assertIn("does not match", result["content"][0]["text"])

    def test_stdio_smoke_test_emits_only_json_rpc(self) -> None:
        messages = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-11-25"},
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ]
        completed = subprocess.run(
            [sys.executable, str(SERVER_PATH)],
            input="".join(json.dumps(message) + "\n" for message in messages),
            text=True,
            capture_output=True,
            check=True,
        )
        output = [json.loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual([message["id"] for message in output], [1, 2])
        self.assertEqual(completed.stderr, "")


class PackageTests(unittest.TestCase):
    def test_manifest_and_marketplace_point_to_packaged_components(self) -> None:
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], PLUGIN_ROOT.name)
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["mcpServers"], "./.mcp.json")
        marketplace = json.loads(
            (REPO_ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        entries = {entry["name"]: entry for entry in marketplace["plugins"]}
        self.assertEqual(
            entries[PLUGIN_ROOT.name]["source"]["path"],
            "./plugins/" + PLUGIN_ROOT.name,
        )

    def test_mcp_manifest_starts_packaged_server(self) -> None:
        manifest = json.loads((PLUGIN_ROOT / ".mcp.json").read_text(encoding="utf-8"))
        server = manifest["mcpServers"]["quantumgridos_hardware_evidence"]
        self.assertEqual(server["command"], "python3")
        self.assertEqual(server["args"], ["./mcp/hardware_evidence_server.py"])
        self.assertTrue(SERVER_PATH.is_file())

    def test_skill_declares_mcp_dependency(self) -> None:
        skill_root = PLUGIN_ROOT / "skills" / "quantum-hardware-evidence-inspector"
        instructions = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        agent_manifest = (skill_root / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertTrue(instructions.startswith("---\nname: quantum-hardware-evidence-inspector\n"))
        self.assertIn('value: "quantumgridos_hardware_evidence"', agent_manifest)

    def test_all_packaged_records_are_explicitly_synthetic(self) -> None:
        fixture_paths = sorted((PLUGIN_ROOT / "records").glob("*/*.json"))
        self.assertEqual(len(fixture_paths), 5)
        for fixture_path in fixture_paths:
            record = json.loads(fixture_path.read_text(encoding="utf-8"))
            self.assertEqual(record["evidence_status"], "synthetic_training_fixture")
            self.assertEqual(fixture_path.stem, record["record_id"])


if __name__ == "__main__":
    unittest.main()
