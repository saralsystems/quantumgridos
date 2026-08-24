# QuantumGridOS Hardware Evidence

This Codex plugin provides a local, dependency-free, read-only MCP server and a focused Skill for reviewing five quantum experiment records:

1. experiment intent;
2. backend capability snapshot;
3. compilation record;
4. execution record;
5. evidence record.

The server reads exact record identifiers from fixed directories and returns SHA-256 retrieval provenance. Its compilation validator checks references, target operation support, two-qubit connectivity, layout uniqueness, and measurement-map consistency. It has no provider client, network discovery, credential handling, job submission, cancellation, reservation, or write tool.

The packaged records are explicitly synthetic teaching fixtures. They demonstrate the record contract; they are not provider or physical-QPU evidence.

Run the tests from the repository root:

```text
python3 -m unittest discover -s plugins/quantumgridos-hardware-evidence/tests -v
```

