# PDF preview recovery

The local PDF compiled successfully and contained the current 217-word abstract.
Its six pages were readable with PyMuPDF. The reported failure was in a browser
preview, whose temporary signed asset link expired at 05:18:39 UTC on 8 November
2026. Browser diagnostics recorded HTTP 404 and displayed "Not Found" on reload
at 05:27 UTC. No compiler error caused that response.

Opened the existing PDF through T3's native Files explorer at
`output/pdf/main.pdf`. The resulting file tab is named `main.pdf`; the native
viewer displayed "1 / 6 pages" and the document text. Removed the obsolete
browser tab through T3's UI and retained the source and native PDF tabs. No
floating window was enabled.

Updated `paper/README.md` to describe the native file-viewer route and explain
why refreshing an expired browser asset address does not renew the link.
No app patch, new server, or compiler change was needed.

Verification: confirmed the expired timestamp, browser 404, current abstract
inside the local PDF, and the recovered native PDF viewer.
