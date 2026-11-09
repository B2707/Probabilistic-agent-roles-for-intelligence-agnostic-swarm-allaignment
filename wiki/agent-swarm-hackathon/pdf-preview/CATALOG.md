# PDF preview handoff

- Compiler: `sh scripts/build-paper.sh`, output `output/pdf/main.pdf`.
- Use T3's native Files explorer to open `output/pdf/main.pdf`, in the tab named
  `main.pdf`. Do not reuse browser addresses at `/api/assets/` after they expire.
- Recovery: close the expired browser preview and open the file from Files.
  Recompiling cannot renew the browser tab's signed address.
- Native source and PDF tabs are available. The user explicitly rejected a
  floating window; keep it disabled.
- Evidence and smoke checks: `Update-1.md` in this directory.
