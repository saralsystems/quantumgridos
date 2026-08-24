# QuantumGridOS Evidence Review plugin

This local Codex plugin implements the five-record and nested-execution mental models from the quantum-classical service chapter of *Pre-Quantum*. It packages one focused Skill with one read-only MCP server. The Skill separates gates, circuits, shots, provider jobs, algorithm iterations, polling, retry, reconciliation, and complete experiment replication before it evaluates record invariants.

The server exposes exactly five tools:

1. `get_request_record`
2. `get_execution_plan`
3. `get_job_snapshot`
4. `get_result_record`
5. `get_operations_summary`

It does not list arbitrary files, accept paths from tool callers, write records, authenticate to providers, submit jobs, cancel jobs, or use the network. It runs on Python 3.9 or later with only the standard library.

## Records directory

By default, the server reads the clearly labeled synthetic fixtures in `records/`. To inspect another local ledger, set `QUANTUMGRIDOS_RECORDS_DIR` to its absolute directory before starting Codex. The directory must contain `requests/`, `plans/`, `jobs/`, `results/`, and `operations/` subdirectories. See the Skill's `references/record-contract.md` for the field contract.

## Test

From the QuantumGridOS repository root:

```bash
python3 -m unittest discover \
  -s plugins/quantumgridos-evidence-review/tests \
  -p 'test_*.py'
```

Validate the package:

```bash
python3 /path/to/plugin-creator/scripts/validate_plugin.py \
  plugins/quantumgridos-evidence-review
```

## Install from the repository marketplace

The repository includes `.agents/plugins/marketplace.json`. After cloning the repository, restart the ChatGPT desktop app, open the Plugins Directory, choose the **QuantumGridOS** marketplace, and install **QuantumGridOS Evidence Review**. Repository marketplace availability can vary by product surface.

The records are evidence inputs, not trusted conclusions. A returned file digest proves which bytes the server read; it does not establish that the record is accurate or that physical quantum hardware ran.
