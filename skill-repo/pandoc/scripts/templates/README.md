# Bundled Templates

Templates bundled with the pandoc cli-me skill. Each is pinned to an upstream
release and verified by SHA-256.

## eisvogel.latex

A clean, customizable LaTeX template for pandoc. Used for professional-looking
PDF output (technical reports, white papers, theses, branded documents).

| Field | Value |
|---|---|
| Upstream | https://github.com/Wandmalfarbe/pandoc-latex-template |
| Version pinned | v3.4.0 (released 2026-02-08) |
| Source archive | https://github.com/Wandmalfarbe/pandoc-latex-template/releases/download/v3.4.0/Eisvogel-3.4.0.zip |
| File extracted | `Eisvogel-3.4.0/eisvogel.latex` |
| SHA-256 | `a2c93461565a5dc27f54487620f5205b45bd159993eba33499955b56a62072da` |
| Size | 31,260 bytes |
| License | BSD-3-Clause (see file header — copyright Pascal Wagler + John MacFarlane) |

To verify the bundled file matches upstream:

```bash
sha256sum eisvogel.latex
```

To update to a newer release: download the new `Eisvogel-VERSION.zip` from
the upstream releases page, extract `eisvogel.latex`, replace this file, and
update the version + SHA-256 in this README.

The bundled template is invoked via `pandoc-cli templates eisvogel INPUT OUTPUT`
which passes `--template <bundled-path>` to pandoc.
