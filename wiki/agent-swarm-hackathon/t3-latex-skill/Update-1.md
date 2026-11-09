# Reusable local LaTeX skill

Created and installed [t3-latex](/Users/msteitieh/.codex/skills/t3-latex/SKILL.md) at the user's request. Invoke it with `$t3-latex`.

The skill captures the working native T3 workflow: source and PDF tabs in the Files side pane, a local Recompile project action, and source-line comments that add context to chat. It records the preference for switching tabs, paragraph source formatting, and the difference between native PDF file tabs and browser previews with expiring links. It does not include this paper's text, Apart class, fonts, or research sources.

The T3 reference explains merging `t3.json` and live saved project actions without replacing unrelated scripts. The live project was read to confirm the action schema and existing commands. Its configuration was left unchanged.

The portable Tectonic helper accepts an input `.tex` file and output directory. It resolves paths before changing to the source directory, supports a restricted desktop PATH, keeps compiler diagnostics, and preserves a good PDF on failure. A relative compiler override exposed a path-resolution issue during implementation; the helper now resolves that executable before changing directories, and the smoke test covers it.

## Validation

The skill-creator validator and shell syntax check passed. The disposable-project smoke test passed real compilation with a relative input, a bibliography, paths with spaces, a relative compiler override, a restricted PATH, offline mode, deliberately invalid LaTeX, and a missing compiler. Failed builds retained the previous PDF and exposed diagnostics. Temporary build directories were removed.

The current paper was also compiled with the helper. Because the user was editing while the skill was created, the last displayed PDF was not a reliable comparison baseline. A single temporary snapshot was built with both the original project command and the new helper. All seven pages had identical extracted text and rendered pixels, including the existing fonts and citations. All skill resource links resolve.

The installed skill includes `SKILL.md`, `agents/openai.yaml`, `references/t3-code.md`, `scripts/build-latex.sh`, and `scripts/smoke-test.py`. The manuscript, current PDF, and existing build action were left untouched by this task.
