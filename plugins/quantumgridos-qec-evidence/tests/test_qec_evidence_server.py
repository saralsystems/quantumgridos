"""Protocol, algebra, and closed-world tests for the QEC evidence MCP server."""

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
SERVER_PATH = PLUGIN_ROOT / "mcp" / "qec_evidence_server.py"
SPEC = importlib.util.spec_from_file_location("quantumgridos_qec_evidence_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
SERVER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SERVER
SPEC.loader.exec_module(SERVER)


class QecEvidenceServerTests(unittest.TestCase):
    def write_record(self, root: Path, kind: str, record_id: str, **fields) -> None:
        target_dir = root / SERVER.KIND_DIRECTORIES[kind]
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / (record_id + ".json")).write_text(
            json.dumps({"record_id": record_id, **fields}), encoding="utf-8"
        )

    def test_lists_five_read_only_closed_world_tools(self) -> None:
        response = SERVER.handle_request(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        tools = response["result"]["tools"]
        self.assertEqual([tool["name"] for tool in tools], [
            "inspect_code_spec",
            "validate_syndrome_schema",
            "compare_distance_runs",
            "audit_fault_tolerance_claim",
            "export_qec_evidence_bundle",
        ])
        for tool in tools:
            self.assertTrue(tool["annotations"]["readOnlyHint"])
            self.assertFalse(tool["annotations"]["destructiveHint"])
            self.assertFalse(tool["annotations"]["openWorldHint"])

    def test_inspects_commuting_independent_code_spec(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_record(
                root, "code", "bit-flip", n=3, k=1, distance=1,
                stabilizer_generators=["ZZI", "IZZ"],
            )
            with patch.dict(os.environ, {SERVER.EVIDENCE_ENV: str(root)}):
                result = SERVER.tool_result("inspect_code_spec", {"code_id": "bit-flip"})
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"]["status"], "pass")
        self.assertEqual(result["structuredContent"]["computedGeneratorRank"], 2)

    def test_rejects_noncommuting_generators_and_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_record(
                root, "code", "bad-code", n=1, k=0, distance=1,
                stabilizer_generators=["X", "Z"],
            )
            with patch.dict(os.environ, {SERVER.EVIDENCE_ENV: str(root)}):
                result = SERVER.tool_result("inspect_code_spec", {"code_id": "bad-code"})
                traversal = SERVER.tool_result("inspect_code_spec", {"code_id": "../secret"})
        self.assertEqual(result["structuredContent"]["status"], "fail")
        self.assertIn("do not commute", " ".join(result["structuredContent"]["findings"]))
        self.assertTrue(traversal["isError"])

    def test_validates_raw_syndrome_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_record(root, "syndrome", "batch-1", records=[{
                "round": 1, "check_id": "Z0Z1", "ancilla": "a01", "basis": "Z",
                "bit": 1, "timestamp": "2026-08-24T00:00:00Z", "provenance": "fixture",
            }])
            with patch.dict(os.environ, {SERVER.EVIDENCE_ENV: str(root)}):
                result = SERVER.tool_result("validate_syndrome_schema", {"syndrome_id": "batch-1"})
        self.assertEqual(result["structuredContent"]["status"], "pass")

    def test_compares_only_compatible_distance_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            common = {
                "code_family": "surface", "circuit_family": "memory-v1",
                "decoder_version": "decoder-v2", "task": "memory",
                "statistics_method": "binomial-interval", "uncertainty": {"kind": "interval"},
            }
            self.write_record(root, "run", "d3", distance=3, logical_error_rate=0.02, **common)
            self.write_record(root, "run", "d5", distance=5, logical_error_rate=0.01, **common)
            with patch.dict(os.environ, {SERVER.EVIDENCE_ENV: str(root)}):
                result = SERVER.tool_result("compare_distance_runs", {"run_ids": ["d3", "d5"]})
        payload = result["structuredContent"]
        self.assertEqual(payload["status"], "compatible")
        self.assertTrue(payload["logicalErrorDecreasesWithDistance"])
        self.assertIn("still requires", payload["boundedConclusion"])

    def test_claim_audit_preserves_missing_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_record(
                root, "claim", "claim-1", proposed_claim="below threshold",
                evidence_rung="below_threshold_scaling", supplied_evidence=["code", "circuit"],
                postselected=True,
            )
            with patch.dict(os.environ, {SERVER.EVIDENCE_ENV: str(root)}):
                result = SERVER.tool_result("audit_fault_tolerance_claim", {"claim_id": "claim-1"})
        payload = result["structuredContent"]
        self.assertEqual(payload["status"], "insufficient")
        self.assertIn("distances", payload["missingEvidence"])
        self.assertTrue(payload["warnings"])

    def test_bundle_returns_digest_manifest_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_record(root, "code", "code-1", n=3, k=1, distance=1, stabilizer_generators=["ZZI", "IZZ"])
            self.write_record(root, "claim", "claim-1", evidence_rung="syndrome_detection", supplied_evidence=[])
            self.write_record(root, "bundle", "bundle-1", artifacts=[
                {"kind": "code", "record_id": "code-1"},
                {"kind": "claim", "record_id": "claim-1"},
            ])
            before = sorted(path.relative_to(root) for path in root.rglob("*"))
            with patch.dict(os.environ, {SERVER.EVIDENCE_ENV: str(root)}):
                result = SERVER.tool_result("export_qec_evidence_bundle", {"bundle_id": "bundle-1"})
            after = sorted(path.relative_to(root) for path in root.rglob("*"))
        payload = result["structuredContent"]
        self.assertEqual(payload["status"], "returned_without_writes")
        self.assertEqual(payload["artifactCount"], 2)
        self.assertRegex(payload["manifestSha256"], r"^[a-f0-9]{64}$")
        self.assertEqual(before, after)

    def test_stdio_smoke_test_emits_only_json_rpc(self) -> None:
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ]
        completed = subprocess.run(
            [sys.executable, str(SERVER_PATH)],
            input="".join(json.dumps(message) + "\n" for message in messages),
            text=True, capture_output=True, check=True,
        )
        output = [json.loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual([message["id"] for message in output], [1, 2])
        self.assertEqual(completed.stderr, "")


class PackageManifestTests(unittest.TestCase):
    def test_plugin_manifest_and_mcp_point_to_packaged_components(self) -> None:
        plugin = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        mcp = json.loads((PLUGIN_ROOT / ".mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["name"], PLUGIN_ROOT.name)
        self.assertEqual(plugin["skills"], "./skills/")
        self.assertEqual(plugin["mcpServers"], "./.mcp.json")
        self.assertEqual(mcp["mcpServers"]["quantumgridos_qec_evidence"]["args"], ["./mcp/qec_evidence_server.py"])

    def test_marketplace_and_skill_are_complete(self) -> None:
        marketplace = json.loads((REPO_ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
        entries = {entry["name"]: entry for entry in marketplace["plugins"]}
        self.assertEqual(entries[PLUGIN_ROOT.name]["source"]["path"], "./plugins/" + PLUGIN_ROOT.name)
        skill = (PLUGIN_ROOT / "skills" / "quantum-error-correction-evidence-reviewer" / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill.startswith("---\nname: quantum-error-correction-evidence-reviewer\n"))
        self.assertNotIn("[TODO:", skill)
        self.assertIn("three passes", skill)
        self.assertIn("extraction rounds", skill)


if __name__ == "__main__":
    unittest.main()
