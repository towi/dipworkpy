#!/usr/bin/env python3
"""Probe: x1.md / x1.pdf — dwex-Darstellungstest.

Jede Sektion besteht aus einer DWEX-Quelle (im PDF abgedruckt) und dem
Graphen, den GENAU diese Quelle erzeugt hat (parse -> render).
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

# ---------------------------------------------------------------- Probe 1: alle Bewegungsarten (dwex-Quelle)
SRC1 = """@dwex
title: x1/1 — alle Bewegungsarten · alle 7 Nationen · alle Feldtypen
desc:  mve durchgezogen/gepunktet, hsup Quadrat, msup Bogen/Diamant, con Klammer, hld nur Icon, rotes X dislodged

map {
  Ala LA 1,1
  Bla L 4,1
  Cla LCB 7,1
  Dla O 10,1
  Ela L 1,5
  Fla LA 4,5
  Gla O 7,5
  Hla LCB 10,5
  Ila LA 1,9
  Jla L 4,9
  Kla O 7,9
  Lla LCB 10,9
  Ala -- Bla
  Bla -- Cla
  Cla -- Dla
  Ala -- Ela
  Bla -- Fla
  Cla -- Gla
  Dla -- Hla
  Ela -- Fla
  Fla -- Gla
  Gla -- Hla
  Ela -- Ila
  Fla -- Jla
  Gla -- Kla
  Hla -- Lla
  Ila -- Jla
  Jla -- Kla
  Kla -- Lla
}

orders {
  Au A Ala mve Bla # mve, Erfolg: durchgezogen
  Fr A Cla mve Bla ! # mve, fehlgeschlagen: gepunktet
  En F Bla hsup Fla # hsup: Quadrat am Ziel
  It A Fla mve Gla # unterstuetzte Bewegung
  Ge A Ela msup Fla # msup implizit: Bogen Ela->Fla->Gla
  Ru F Gla msup Kla # msup-Fallback (Kla ohne mve): Diamant
  Tu A Hla mve Lla # konvoierte Bewegung
  Fr F Kla con Hla # con: Klammer-Bogen Hla->Lla
  Au F Ila hld # hld: kein Pfeil, nur Icon
  En A Jla mve Ila !> # fehlgeschlagen + vertrieben: gepunktet + rotes X
}
@end
"""

doc1 = parse(SRC1)
render_png(doc1, OUT / "x1_probe_all_orders.png")

# ---------------------------------------------------------------- Probe 2+3: echte FAIL-Fälle
def render_real_case(case_id: str, out_name: str):
    tc = None
    with open(BASE / "testdata/diplomacy-research/standard_no_press.jsonl") as f:
        for cand in stream_test_cases(f, max_games=1000):
            if cand.id == case_id:
                tc = cand
                break
    assert tc is not None, case_id
    er = evaluate_test_case(tc, keep_details=True)
    cls = classify_dipnet(tc, er.diffs)
    source = build_dipnet_dwex(tc, er, cls)
    doc = parse(source)
    out = OUT / out_name
    render_png(doc, out)
    return out.name, source, cls


n2, src2, cls2 = render_real_case("D619QzLd0FKfXi4m_S1904M", "x1_probe_case_c2.png")
n3, src3, cls3 = render_real_case("cSaeUT4h0rewXGWH_S1908M", "x1_probe_case_c1.png")

# ---------------------------------------------------------------- x1.md
md = f"""# x1 — DWES-Darstellungsprobe

Jede Sektion: **DWEX-Quelle abgedruckt → der Graph darunter ist aus GENAU
dieser Quelle gerendert** (parse → render). Die roten Ringe (`::error`)
markieren die zwischen DipNet und uns divergierenden Orders.

## 1. Alle Bewegungsarten (synthetische Karte)

```dwex
{SRC1}
```

![alle Bewegungsarten](fail-report/img/x1_probe_all_orders.png)

## 2. Realer FAIL-Fall C2: D619QzLd0FKfXi4m_S1904M ({cls2[1]})

```dwex
{src2}
```

![C2](fail-report/img/{n2})

## 3. Realer FAIL-Fall C1: cSaeUT4h0rewXGWH_S1908M ({cls3[1]})

```dwex
{src3}
```

![C1](fail-report/img/{n3})
"""
(BASE / "x1.md").write_text(md, encoding="utf-8")

markdown_to_pdf(BASE / "x1.md", BASE / "x1.pdf")
print("Fertig: x1.md + x1.pdf")
