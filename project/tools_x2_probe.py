#!/usr/bin/env python3
"""Probe: x2.md / x2.pdf — Voronoi-Grenzen (`borders(fences)`).

Die 2. Grafik aus x1 (realer FAIL-Fall D619QzLd0FKfXi4m_S1904M, volles
Standard-Brett) wird einmal mit `borders(edges)` (Referenz) und einmal mit
`borders(fences)` gerendert: statt der Verbindungslinien zwischen den
Feldzentren werden die Mittelsenkrechten zwischen angrenzenden Feldern
gezeichnet — wie Grenzzäune auf einer Karte.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "project"))

from dipworkpy.tools.dwex.lang import parse
from dipworkpy.tools.dwex.render_png import render_png

from test_data_pipeline.dipnet_parser import stream_test_cases
from test_data_pipeline.evaluator import evaluate_test_case

from tools_fail_report import (  # type: ignore
    IMG_DIR,
    build_dipnet_dwex,
    classify_dipnet,
    markdown_to_pdf,
)

OUT = IMG_DIR
OUT.mkdir(parents=True, exist_ok=True)

CASE = "D619QzLd0FKfXi4m_S1904M"

tc = None
with open(BASE / "testdata/diplomacy-research/standard_no_press.jsonl") as f:
    for cand in stream_test_cases(f, max_games=1000):
        if cand.id == CASE:
            tc = cand
            break
assert tc is not None, CASE
er = evaluate_test_case(tc, keep_details=True)
cls = classify_dipnet(tc, er.diffs)
src_edges = build_dipnet_dwex(tc, er, cls)

# fences variant: add the borders pragma to the same source
assert "pragmas {" in src_edges
src_fences = src_edges.replace("pragmas {", "pragmas {\n  borders(fences)", 1)


def render(source: str, name: str) -> str:
    doc = parse(source)
    out = OUT / name
    render_png(doc, out)
    return out.name


n_edges = render(src_edges, "x2_probe_case_edges.png")
n_fences = render(src_fences, "x2_probe_case_fences.png")

md = f"""# x2 — Voronoi-Grenzen (`borders(fences)`)

Dasselbe Brett wie x1/Grafik 2 (realer FAIL-Fall `{CASE}`), einmal mit den
gewöhnlichen Verbindungslinien (`borders(edges)`, Referenz) und einmal mit
Voronoi-artigen Grenzlinien (`borders(fences)`: Mittelsenkrechte zwischen
jeder angrenzenden Feldpaarung — Grenz-Zaun-Optik statt Knoten-Verbindungen).

## 1. Referenz — borders(edges)

```dwex
{src_edges}
```

![edges](fail-report/img/{n_edges})

## 2. borders(fences)

```dwex
{src_fences}
```

![fences](fail-report/img/{n_fences})
"""
(BASE / "x2.md").write_text(md, encoding="utf-8")

markdown_to_pdf(BASE / "x2.md", BASE / "x2.pdf")
print("Fertig: x2.md + x2.pdf")
