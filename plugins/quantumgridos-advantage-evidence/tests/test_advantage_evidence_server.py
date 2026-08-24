"""Protocol, evidence-boundary, and packaging tests for the advantage server."""

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
SERVER_PATH = PLUGIN_ROOT / "mcp" / "advantage_evidence_server.py"
SPEC = importlib.util.spec_from_file_location(
    "quantumgridos_advantage_evidence_server", SERVER_PATH
)
assert SPEC is not None and SPEC.loader is not None
SERVER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SERVER
SPEC.loader.exec_module(SERVER)


class AdvantageEvidenceServerTests(unittest.TestCase):
    def write_record(
        self, root: Path, kind: str, record_id: str, **fields: object
    ) -> Path:
        target_dir = root / SERVER.KIND_DIRECTORIES[kind]
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / (record_id + ".json")
        target.write_text(
            json.dumps({"record_id": record_id, **fields}, sort_keys=True),
            encoding="utf-8",
        )
        return target

    def contract_fields(self) -> dict[str, object]:
        return {
            "input_family": "declared weighted graphs",
            "required_output": "binary partition",
            "correctness_test": "recompute cut value",
            "approximation_rule": "compare with exact optimum when feasible",
            "counted_resources": ["preprocess", "execute", "validate"],
            "intended_user": "learning developer",
        }

    def test_lists_six_read_only_closed_world_tools(self) -> None:
        response = SERVER.handle_request(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        tools = response["result"]["tools"]
        self.assertEqual(
            [tool["name"] for tool in tools],
            [
                "read_problem_contract",
                "list_baselines",
                "read_experiment_manifest",
                "compare_contract_digests",
                "list_missing_evidence",
                "render_evidence_ledger",
            ],
        )
        for tool in tools:
            self.assertTrue(tool["annotations"]["readOnlyHint"])
            self.assertFalse(tool["annotations"]["destructiveHint"])
            self.assertFalse(tool["annotations"]["openWorldHint"])

    def test_reads_complete_contract_and_reports_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_record(root, "contract", "cut-task", **self.contract_fields())
            with patch.dict(os.environ, {SERVER.EVIDENCE_ENV: str(root)}):
                result = SERVER.tool_result(
                    "read_problem_contract", {"contract_id": "cut-task"}
                )
        payload = result["structuredContent"]
        self.assertEqual(payload["status"], "pass")
        self.assertRegex(payload["contractDigest"], r"^[a-f0-9]{64}$")
        self.assertEqual(payload["missingFields"], [])

    def test_rejects_incomplete_contract_and_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_record(root, "contract", "incomplete", input_family="graphs")
            with patch.dict(os.environ, {SERVER.EVIDENCE_ENV: str(root)}):
                incomplete = SERVER.tool_result(
                    "read_problem_contract", {"contract_id": "incomplete"}
                )
                traversal = SERVER.tool_result(
                    "read_problem_contract", {"contract_id": "../secret"}
                )
        self.assertEqual(incomplete["structuredContent"]["status"], "incomplete")
        self.assertIn("required_output", incomplete["structuredContent"]["missingFields"])
        self.assertTrue(traversal["isError"])

    def test_lists_named_baselines_under_one_contract(self) -> None:
        digest = "a" * 64
        common = {
            "contract_digest": digest,
            "configuration": {"seed": 23},
            "environment": "python",
            "stopping_rule": "complete",
            "validator_id": "cut-validator",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_record(
                root,
                "baseline",
                "exact-v1",
                algorithm="enumeration",
                implementation_version="1.0",
                **common,
            )
            self.write_record(
                root,
                "baseline",
                "greedy-v2",
                algorithm="greedy",
                implementation_version="2.0",
                **common,
            )
            with patch.dict(os.environ, {SERVER.EVIDENCE_ENV: str(root)}):
                result = SERVER.tool_result(
                    "list_baselines",
                    {
                        "baseline_ids": ["exact-v1", "greedy-v2"],
                        "contract_digest": digest,
                    },
                )
        payload = result["structuredContent"]
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(len(payload["baselines"]), 2)
        self.assertTrue(all(item["contractMatches"] for item in payload["baselines"]))

    def test_physical_hardware_manifest_requires_hardware_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_record(
                root,
                "experiment",
                "device-run",
                contract_digest="b" * 64,
                evidence_type="physical_quantum_hardware",
                artifact_digest="c" * 64,
                environment="provider",
                raw_output="result-1",
                validator_id="validator-1",
                limitations=["bounded task"],
            )
            with patch.dict(os.environ, {SERVER.EVIDENCE_ENV: str(root)}):
                result = SERVER.tool_result(
                    "read_experiment_manifest", {"experiment_id": "device-run"}
                )
        payload = result["structuredContent"]
        self.assertEqual(payload["status"], "incomplete")
        self.assertIn("hardware_identity", payload["missingFields"])
        self.assertIn("sampling_policy", payload["missingFields"])

    def test_compares_contract_digests_without_equating_fairness(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract_path = self.write_record(
                root, "contract", "contract-1", **self.contract_fields()
            )
            digest = __import__("hashlib").sha256(contract_path.read_bytes()).hexdigest()
            self.write_record(
                root,
                "baseline",
                "baseline-1",
                contract_digest=digest,
                algorithm="exact",
                implementation_version="1",
                configuration={},
                environment="python",
                stopping_rule="complete",
                validator_id="validator-1",
            )
            self.write_record(
                root,
                "experiment",
                "experiment-1",
                contract_digest=digest,
                evidence_type="plan_only",
                artifact_digest="d" * 64,
                environment="none",
                raw_output="none",
                validator_id="validator-1",
                limitations=["not executed"],
            )
            with patch.dict(os.environ, {SERVER.EVIDENCE_ENV: str(root)}):
                result = SERVER.tool_result(
                    "compare_contract_digests",
                    {
                        "record_refs": [
                            {"kind": "contract", "record_id": "contract-1"},
                            {"kind": "baseline", "record_id": "baseline-1"},
                            {"kind": "experiment", "record_id": "experiment-1"},
                        ]
                    },
                )
        payload = result["structuredContent"]
        self.assertTrue(payload["allMatch"])
        self.assertIn("not fair tuning", payload["limitations"][0])

    def test_decision_gate_preserves_missing_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_record(
                root,
                "gate",
                "pilot-gate",
                action="pilot",
                supplied_evidence=["problem_contract", "classical_baseline"],
            )
            with patch.dict(os.environ, {SERVER.EVIDENCE_ENV: str(root)}):
                result = SERVER.tool_result(
                    "list_missing_evidence", {"gate_id": "pilot-gate"}
                )
        payload = result["structuredContent"]
        self.assertEqual(payload["status"], "insufficient")
        self.assertIn("user_outcome", payload["missingEvidence"])
        self.assertIn("stop_condition", payload["missingEvidence"])

    def test_renders_acyclic_ledger_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_record(root, "contract", "contract-1", **self.contract_fields())
            self.write_record(
                root,
                "baseline",
                "baseline-1",
                contract_digest="a" * 64,
                algorithm="exact",
                implementation_version="1",
                configuration={},
                environment="python",
                stopping_rule="complete",
                validator_id="validator-1",
            )
            self.write_record(
                root,
                "gate",
                "gate-1",
                action="learn",
                supplied_evidence=["problem_contract"],
            )
            self.write_record(
                root,
                "ledger",
                "ledger-1",
                artifacts=[
                    {
                        "artifact_id": "contract",
                        "kind": "contract",
                        "record_id": "contract-1",
                        "depends_on": [],
                    },
                    {
                        "artifact_id": "baseline",
                        "kind": "baseline",
                        "record_id": "baseline-1",
                        "depends_on": ["contract"],
                    },
                    {
                        "artifact_id": "decision",
                        "kind": "gate",
                        "record_id": "gate-1",
                        "depends_on": ["baseline"],
                    },
                ],
            )
            before = sorted(path.relative_to(root) for path in root.rglob("*"))
            with patch.dict(os.environ, {SERVER.EVIDENCE_ENV: str(root)}):
                result = SERVER.tool_result(
                    "render_evidence_ledger", {"ledger_id": "ledger-1"}
                )
            after = sorted(path.relative_to(root) for path in root.rglob("*"))
        payload = result["structuredContent"]
        self.assertEqual(payload["status"], "rendered_without_writes")
        self.assertEqual(payload["topologicalOrder"], ["contract", "baseline", "decision"])
        self.assertEqual(before, after)

    def test_rejects_unresolved_ledger_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_record(root, "contract", "contract-1", **self.contract_fields())
            self.write_record(
                root,
                "ledger",
                "bad-ledger",
                artifacts=[
                    {
                        "artifact_id": "contract",
                        "kind": "contract",
                        "record_id": "contract-1",
                        "depends_on": ["missing"],
                    }
                ],
            )
            with patch.dict(os.environ, {SERVER.EVIDENCE_ENV: str(root)}):
                result = SERVER.tool_result(
                    "render_evidence_ledger", {"ledger_id": "bad-ledger"}
                )
        self.assertTrue(result["isError"])
        self.assertIn("unresolved dependencies", result["content"][0]["text"])

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
    def test_plugin_manifest_and_mcp_point_to_packaged_components(self) -> None:
        plugin = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        mcp = json.loads((PLUGIN_ROOT / ".mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["name"], PLUGIN_ROOT.name)
        self.assertEqual(plugin["skills"], "./skills/")
        self.assertEqual(plugin["mcpServers"], "./.mcp.json")
        self.assertEqual(
            mcp["mcpServers"]["quantumgridos_advantage_evidence"]["args"],
            ["./mcp/advantage_evidence_server.py"],
        )

    def test_marketplace_and_skill_are_complete(self) -> None:
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
        self.assertEqual(entries[PLUGIN_ROOT.name]["category"], "Developer Tools")
        skill = (
            PLUGIN_ROOT
            / "skills"
            / "quantum-advantage-evidence-reviewer"
            / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertTrue(skill.startswith("---\nname: quantum-advantage-evidence-reviewer\n"))
        self.assertNotIn("[TODO:", skill)
        self.assertIn("Trace circuit and execution boundaries", skill)
        self.assertIn("compare_contract_digests", skill)


if __name__ == "__main__":
    unittest.main()
