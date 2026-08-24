# QuantumGridOS Advantage Evidence

This plugin packages the Chapter 23 quantum-advantage evidence-review Skill and a dependency-free, read-only local MCP server.

The server reads JSON records beneath the directory named by `QUANTUMGRIDOS_ADVANTAGE_EVIDENCE_DIR`. It exposes six tools:

- `read_problem_contract`
- `list_baselines`
- `read_experiment_manifest`
- `compare_contract_digests`
- `list_missing_evidence`
- `render_evidence_ledger`

The tools validate structure and declared relationships. They do not authenticate scientific claims, contact providers, execute benchmarks, write files, or change evidence records.

Run the package tests with:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```
