# Project Documentation — how to view

This directory contains the implementation-level documentation for DipworkPy. The entry point is **[index.md](index.md)**.

## Three ways to view

### 1. Read on GitHub (zero setup)

Open [index.md](index.md) directly in the GitHub UI — markdown and inline PNGs render automatically. This is the recommended path if you just want to read.

### 2. Read locally (zero setup)

Any markdown viewer works:

- **VS Code / Cursor**: open the folder, press `Cmd/Ctrl+Shift+V` on any `.md` file for a side-by-side preview.
- **JetBrains IDEs** (PyCharm, IntelliJ): open the markdown file and click the preview toggle in the gutter.
- **Browser**: a quick `python -m http.server -d project/doc 8000` exposes the tree at `http://localhost:8000/` (you'll see directory listings; click into `index.md` after rendering it elsewhere — browsers don't render `.md` natively).

### 3. Render as a static HTML site (Zensical, recommended for polished output)

Config lives at `project/mkdocs.yml` — Zensical reads MkDocs config files natively. The docs deps live in the `docs` group of `pyproject.toml` and are installed on-demand by the Makefile:

```bash
cd project
make docs        # renders all DDL PNGs, regenerates EXAMPLES.md, builds doc-site/
make docs-serve  # live-preview at http://127.0.0.1:8000/
make docs-clean  # remove doc-site/ and the mirrored _design/ dir
```

`make docs` chains:

1. `make examples` → re-renders all `.dwex` PNGs and regenerates `EXAMPLES.md`
2. `make docs-prep` → mirrors cross-tree files (spec, plan, status, NOTATION.md) into `doc/_design/` so the rendered site is offline-self-contained
3. `uv sync --group docs` → installs `zensical` into the uv-managed env
4. `zensical build` → reads `mkdocs.yml`, emits HTML into `doc-site/`

Output dir + `doc/_design/` are git-ignored and regenerated on every build.

Equivalent manual invocation:

```bash
cd project
uv sync --group docs
make examples
make docs-prep
uv run zensical build
```

Zensical is the successor to MkDocs (by the Material for MkDocs team), 4-5× faster on incremental builds and natively reads `mkdocs.yml`. The build runs warning-free against this project's config.

## Where the DDL diagrams come from

The 14 DDL examples in [EXAMPLES.md](EXAMPLES.md) (and their PNGs in [`examples/dwex/`](examples/dwex/)) are generated from `.dwex` source files. Each `.dwex` parses into a `Situation` plus an expected `ConflictResolution`, so every diagram in the docs is also a regression test.

To regenerate all PNGs and rebuild `EXAMPLES.md`:

```bash
cd project
make examples
```

This runs `dipworkpy.tools.dwex render-all` (matplotlib → PNG) and `dipworkpy.tools.dwex.generate_index` (PNG-embedded markdown). Commit the PNG changes alongside `.dwex` source changes — GitHub renders them inline.

## How this directory relates to the top-level `docs/`

Two doc trees live in this repo:

| Path | Purpose | Audience |
|------|---------|----------|
| `project/doc/` *(this one)* | Implementation-level: pipeline, services, DDL examples, test analyses | Developers / maintainers |
| `docs/` *(repo root)* | Game-level: Diplomacy rules, Atari variant, rule interpretations | Players / GMs |

The top-level `docs/` is published via Jekyll/GitHub Pages. The `project/doc/` tree is browsed directly on GitHub or rendered locally via MkDocs.
