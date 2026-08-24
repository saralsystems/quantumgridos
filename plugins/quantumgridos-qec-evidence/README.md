# QuantumGridOS QEC Evidence

This Codex plugin packages a focused QEC evidence-review Skill and a dependency-free, read-only local MCP server.

The server exposes five bounded tools for code specifications, syndrome schemas, compatible distance-run comparisons, fault-tolerance claim audits, and digest-only evidence bundles. It has no search, arbitrary path, network, authentication, provider submission, decoder mutation, physical correction, or file-write tool.

By default, records are read from the plugin's `records/` directory. Set `QUANTUMGRIDOS_QEC_EVIDENCE_DIR` to an absolute local fixture directory when testing or reviewing a separate immutable evidence collection.

Run the tests with:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```
