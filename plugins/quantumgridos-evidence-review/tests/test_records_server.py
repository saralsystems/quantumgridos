"""Protocol and filesystem-boundary tests for the local records MCP server."""

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
SERVER_PATH = PLUGIN_ROOT / "mcp" / "records_server.py"
SPEC = importlib.util.spec_from_file_location("quantumgridos_records_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
SERVER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SERVER
SPEC.loader.exec_module(SERVER)


class RecordsServerTests(unittest.TestCase):
    def make_record(self, root: Path, directory: str, record_id: str) -> None:
        target_dir = root / directory
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / (record_id + ".json")).write_text(
            json.dumps({"record_id": record_id, "value": 7}),
            encoding="utf-8",
        )

    def test_lists_five_read_only_closed_world_tools(self) -> None:
        response = SERVER.handle_request(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        tools = response["result"]["tools"]
        self.assertEqual(len(tools), 5)
        self.assertEqual(
            [tool["name"] for tool in tools],
            [
                "get_request_record",
                "get_execution_plan",
                "get_job_snapshot",
                "get_result_record",
                "get_operations_summary",
            ],
        )
        for tool in tools:
            self.assertTrue(tool["annotations"]["readOnlyHint"])
            self.assertFalse(tool["annotations"]["destructiveHint"])
            self.assertFalse(tool["annotations"]["openWorldHint"])

    def test_reads_exact_record_and_returns_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_record(root, "requests", "request-001")
            with patch.dict(os.environ, {SERVER.RECORDS_ENV: str(root)}):
                result = SERVER.tool_result(
                    SERVER.TOOLS_BY_NAME["get_request_record"],
                    {"record_id": "request-001"},
                )
        self.assertFalse(result["isError"])
        payload = result["structuredContent"]
        self.assertEqual(payload["recordKind"], "request")
        self.assertEqual(payload["record"]["value"], 7)
        self.assertRegex(payload["sha256"], r"^[a-f0-9]{64}$")

    def test_rejects_traversal_and_unknown_arguments(self) -> None:
        tool = SERVER.TOOLS_BY_NAME["get_result_record"]
        traversal = SERVER.tool_result(tool, {"record_id": "../secret"})
        extra = SERVER.tool_result(tool, {"record_id": "safe", "path": "/tmp"})
        self.assertTrue(traversal["isError"])
        self.assertTrue(extra["isError"])

    def test_rejects_internal_record_id_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target_dir = root / "jobs"
            target_dir.mkdir()
            (target_dir / "job-001.json").write_text(
                json.dumps({"record_id": "job-002"}), encoding="utf-8"
            )
            with patch.dict(os.environ, {SERVER.RECORDS_ENV: str(root)}):
                result = SERVER.tool_result(
                    SERVER.TOOLS_BY_NAME["get_job_snapshot"],
                    {"record_id": "job-001"},
                )
        self.assertTrue(result["isError"])
        self.assertIn("does not match", result["content"][0]["text"])

    def test_rejects_symlink_that_resolves_outside_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "records"
            target_dir = root / "requests"
            target_dir.mkdir(parents=True)
            outside = base / "outside.json"
            outside.write_text(json.dumps({"record_id": "request-001"}), encoding="utf-8")
            try:
                (target_dir / "request-001.json").symlink_to(outside)
            except (NotImplementedError, OSError):
                self.skipTest("symbolic links are unavailable")
            with patch.dict(os.environ, {SERVER.RECORDS_ENV: str(root)}):
                result = SERVER.tool_result(
                    SERVER.TOOLS_BY_NAME["get_request_record"],
                    {"record_id": "request-001"},
                )
        self.assertTrue(result["isError"])
        self.assertIn("outside", result["content"][0]["text"])

    def test_rejects_record_larger_than_one_mebibyte(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target_dir = root / "results"
            target_dir.mkdir()
            (target_dir / "result-001.json").write_bytes(b" " * (1024 * 1024 + 1))
            with patch.dict(os.environ, {SERVER.RECORDS_ENV: str(root)}):
                result = SERVER.tool_result(
                    SERVER.TOOLS_BY_NAME["get_result_record"],
                    {"record_id": "result-001"},
                )
        self.assertTrue(result["isError"])
        self.assertIn("1 MiB", result["content"][0]["text"])

    def test_negotiates_supported_protocol_and_handles_batch(self) -> None:
        response = SERVER.handle_request(
            {
                "jsonrpc": "2.0",
                "id": "init",
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18"},
            }
        )
        self.assertEqual(response["result"]["protocolVersion"], "2025-06-18")
        batch = SERVER.process_payload(
            [
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "ping"},
            ]
        )
        self.assertEqual(batch, [{"jsonrpc": "2.0", "id": 2, "result": {}}])

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


class PackageManifestTests(unittest.TestCase):
    def test_plugin_manifest_points_to_packaged_components(self) -> None:
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], PLUGIN_ROOT.name)
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["mcpServers"], "./.mcp.json")
        self.assertTrue((PLUGIN_ROOT / "skills").is_dir())
        self.assertTrue((PLUGIN_ROOT / ".mcp.json").is_file())

    def test_mcp_manifest_starts_the_packaged_server(self) -> None:
        manifest = json.loads((PLUGIN_ROOT / ".mcp.json").read_text(encoding="utf-8"))
        server = manifest["mcpServers"]["quantumgridos_records"]
        self.assertEqual(server["command"], "python3")
        self.assertEqual(server["cwd"], ".")
        self.assertEqual(server["args"], ["./mcp/records_server.py"])
        self.assertTrue(SERVER_PATH.is_file())

    def test_repository_marketplace_points_to_plugin(self) -> None:
        marketplace = json.loads(
            (REPO_ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        entries = {entry["name"]: entry for entry in marketplace["plugins"]}
        entry = entries[PLUGIN_ROOT.name]
        self.assertEqual(entry["source"]["source"], "local")
        self.assertEqual(entry["source"]["path"], "./plugins/" + PLUGIN_ROOT.name)

    def test_skill_is_complete_and_declares_mcp_dependency(self) -> None:
        skill_root = PLUGIN_ROOT / "skills" / "quantum-service-evidence-reviewer"
        instructions = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        agent_manifest = (skill_root / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        )
        self.assertTrue(instructions.startswith("---\nname: quantum-service-evidence-reviewer\n"))
        self.assertNotIn("[TODO:", instructions)
        self.assertIn('value: "quantumgridos_records"', agent_manifest)

    def test_all_training_fixtures_are_explicitly_synthetic(self) -> None:
        fixture_paths = sorted((PLUGIN_ROOT / "records").glob("*/*.json"))
        self.assertEqual(len(fixture_paths), 5)
        for fixture_path in fixture_paths:
            record = json.loads(fixture_path.read_text(encoding="utf-8"))
            self.assertEqual(record["evidence_status"], "synthetic_training_fixture")
            self.assertEqual(fixture_path.stem, record["record_id"])


if __name__ == "__main__":
    unittest.main()
