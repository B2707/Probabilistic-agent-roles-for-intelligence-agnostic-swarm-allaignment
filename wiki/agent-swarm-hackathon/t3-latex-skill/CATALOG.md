# Local LaTeX skill handoff

The reusable skill is installed at [/Users/msteitieh/.codex/skills/t3-latex/SKILL.md](/Users/msteitieh/.codex/skills/t3-latex/SKILL.md). Its invocation is `$t3-latex`. It is discoverable with normal automatic selection enabled.

It sets up local LaTeX compilation with T3 native source and PDF file tabs, a Recompile action, and line selection for chat. Read its T3 reference when configuring actions or repairing preview behavior. Reuse existing project builds; copy its Tectonic helper only when a project needs one. The skill does not provide the Apart paper template or a simultaneous source/PDF split.

Run its behavioral smoke test with:

```sh
python3 /Users/msteitieh/.codex/skills/t3-latex/scripts/smoke-test.py
```

Skill validation, build success and failure behavior, offline mode, path handling, and parity with the current paper's original build all passed. [Update 1](Update-1.md) records the verification. Existing project tooling and manuscript content were not changed. No pending work remains for this request.
