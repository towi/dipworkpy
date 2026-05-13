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

### 3. Render as a static HTML site (MkDocs, recommended for polished output)

Pip-install MkDocs once, then serve:

```bash
pip install mkdocs mkdocs-material
cd project
mkdocs serve
```

Open `http://127.0.0.1:8000/`. Live-reloads on save. Use `mkdocs build` for a static `site/` directory you can deploy anywhere.

The expected `project/mkdocs.yml`:

```yaml
site_name: DipworkPy Docs
docs_dir: doc
nav:
  - Home: index.md
  - Pipeline:
      - Phases: PHASES.md
      - Geography: GEOGRAPHY.md
  - Examples (DDL): EXAMPLES.md
  - Test analyses:
      - DATC: DATC_ANALYSIS.md
      - DipNet clusters: DIPNET_CLUSTERS.md
      - Test expansion: TEST_EXPANSION.md
  - Tasks: tasks/README.md
theme:
  name: material
markdown_extensions:
  - admonition
  - pymdownx.details
  - pymdownx.superfences
```

Copy that as `project/mkdocs.yml` to enable Option 3.

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
