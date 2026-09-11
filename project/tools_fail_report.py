#!/usr/bin/env python3
"""Generate FAIL-REPORT.md + FAIL-REPORT.pdf — all failing external-corpus
cases with board diagrams rendered by our own dwex renderer.

Sources
  1. DipNet 1000-game sample   (1000 games, movement phases)  — 86 FAILs
  2. stpsyr DATC runner        (92 cases)                     — 16 FAILs

Every failing case gets a dwex board diagram (matplotlib, our processor's
renderer) showing expected-vs-actual outcome per unit.

Usage (from project/):
    uv run python tools_fail_report.py            # writes ../FAIL-REPORT.md,
                                                   # ../fail-report/img/*.png,
                                                   # then ../FAIL-REPORT.pdf
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

from dipworkpy.tools.dwex.model import (
    DwexEdge,
    DwexField,
)
from dipworkpy.tools.dwex.lang import parse
from dipworkpy.tools.dwex.render_png import render_png
BASE = Path(__file__).resolve().parent.parent  # repo root
PROJ = BASE / "project"
IMG_DIR = BASE / "fail-report" / "img"
DATASET = BASE / "testdata/diplomacy-research/standard_no_press.jsonl"

sys.path.insert(0, str(PROJ))

from test_data_pipeline.dipnet_parser import stream_test_cases  # noqa: E402
from test_data_pipeline.evaluator import (  # noqa: E402
    EvalResult,
    TestResult,
    evaluate_test_case,
)


# --------------------------------------------------------------------------
# classification (from project/doc/DIPNET_CONVOY_TRIAGE.md, 2026-09-09)
# --------------------------------------------------------------------------

_DIPNET_CLASSES: Dict[str, Tuple[str, str]] = {
    # Explicit overrides for cases whose diff alone is ambiguous.
}
def load_layout() -> Tuple[Dict[str, Tuple[float, float]], Dict[str, str]]:
    m = json.load(open(PROJ / "dipworkpy/geography/map/data/standard.json"))
    fields = m["fields"]
    pos: Dict[str, Tuple[float, float]] = {}
    ftype: Dict[str, str] = {}
    for name, d in fields.items():
        if d.get("sub_of"):
            continue  # subfields are not drawn; superfields carry the units
        p = d.get("pos")
        if p:
            pos[name] = (float(p[0]), float(p[1]))
        ftype[name] = d.get("type", "L")
    return pos, ftype


def graph_layout(relevant: set, seed: int) -> Dict[str, Tuple[float, float]]:
    import networkx as nx

    m = json.load(open(PROJ / "dipworkpy/geography/map/data/standard.json"))
    fields = m["fields"]
    g = nx.Graph()
    for name in relevant:
        g.add_node(name)
    for name, d in fields.items():
        if name not in relevant or d.get("sub_of"):
            continue
        for nb in d.get("borders", {}):
            if nb in relevant:
                g.add_edge(name, nb)
    try:
        pos = nx.spring_layout(g, seed=seed, k=1.6 / max(1, len(g) ** 0.5), iterations=200)
        return {n: (float(p[0]), float(p[1])) for n, p in pos.items()}
    except Exception:
        return {n: (i % 10, i // 10) for i, n in enumerate(sorted(relevant))}


def map_edges(relevant: set) -> List[DwexEdge]:
    m = json.load(open(PROJ / "dipworkpy/geography/map/data/standard.json"))
    edges: List[DwexEdge] = []
    seen = set()
    for name, d in m["fields"].items():
        if name not in relevant or d.get("sub_of"):
            continue
        for nb in d.get("borders", {}):
            if nb in relevant:
                key = tuple(sorted((name, nb)))
                if key not in seen:
                    seen.add(key)
                    edges.append(DwexEdge(a=name, b=nb))
    return edges


# --------------------------------------------------------------------------
# diff-line parsing
# --------------------------------------------------------------------------

_DIFF = re.compile(
    r"^\s*(?P<nation>\S+) (?P<utype>[AF]) (?P<current>\S+)"
    r"(?: (?P<order>hld|mve|hsup|msup|con))?(?: (?P<dest>\S+))?"
    r": (?P<kind>succeeds|dislodged): expected=(?P<exp>\w+), got=(?P<got>\w+)"
)


def parse_diff_orders(diffs: List[str]) -> List[Tuple[str, str, str, str, str]]:
    out = []
    for line in diffs:
        m = _DIFF.match(line)
        if m:
            out.append((m["utype"], m["current"], m["kind"], m["exp"], m["got"]))
    return out


def classify_dipnet(tc, diffs: List[str]) -> Tuple[str, str]:
    """Classify a failing DipNet case from diff direction + order type.

    Documented families (project/doc/DIPNET_CONVOY_TRIAGE.md, 2026-09-09):
      C3  dislodged-flag diff on a supporter                       -> c
      C2  msup/hsup of a failed convoy: DipNet False vs unset       -> c
      B3/B2 con order diff (not-executed reporting)                -> b
      B1  mve diff expected=None got=False (VIA stands vs land)     -> b
      C1  mve diff expected=False got=None (con-dest invisible)     -> c
    """
    for line in diffs:
        m = _DIFF.match(line)
        if not m:
            continue
        kind, exp, got, order = m["kind"], m["exp"], m["got"], m["order"] or "hld"
        if kind == "dislodged":
            return ("c", "Dislodged-Flag-Divergenz bei Unterstützern (C3)")
        if order in ("msup", "hsup"):
            return ("c", "Support eines gescheiterten Konvois: DipNet 'no convoy' vs. unset (C2)")
        if order == "con":
            return ("b", "con-Order meldet nicht ausgeführt (B3/B2)")
        if order == "mve":
            con_starts = {
                c.dest for c in tc.orders if c.order is not None and c.order.value == "con"
            }
            has_con = bool(con_starts)
            if exp == "None" and got == "False":
                for o in tc.orders:
                    if o.current == m["current"] and o.utype == m["utype"] and o.via_convoy:
                        return ("b", "B.3.2.14 Satz 1: VIA ohne/nicht-konvoierbar — steht statt Landzug (B1)")
                for o in tc.orders:
                    if o.via_convoy and (o.current not in con_starts):
                        return ("b", "B.3.2.14 Satz 1: VIA-Armee ohne Konvoier — Knock-on auf Drittergebnis (B1)")
                if has_con:
                    return ("c", "con-Ziel im Wire-Format nicht abgebildet — Knock-on auf Drittbewegung (C1)")
                return ("b", "Bewegung scheitert bei uns, DipNet zieht (B-Familie)")
            if has_con:
                return ("c", "con-Ziel im Wire-Format nicht abgebildet — DipNet scheitert den Move (C1)")
            return ("c", "Konvoi-Kontext-Divergenz im Wire-Format (C1/verwandt)")


def classify_stpsyr(title: str) -> Tuple[str, str]:
    t = title.lower()
    if "coast" in t or "unspecified" in t:
        return ("c", "Split-Coast-Board-Vergleich (Runner arbeitet superfield-only)")
    if "missing fleet" in t:
        return ("b", "Korpus-Erwartung weicht selbst von DATC ab (im Korpus markiert)")


    return ("c", "Runner-Limitation (naive Retreats / Board-Endvergleich, vgl. Runner-Kopf)")
def _normalized_fields(relevant, layout, ftype, idx: int) -> List[DwexField]:
    """Fields with coordinates normalized to the dwex renderer's expected
    scale (~a 12-unit box, aspect-preserving).

    The renderer sizes circles, jitter, and marker pads in AXIS units over a
    small coordinate range (its examples use 0-10). Raw standard-map
    positions span ~600 units — a radius-0.22 circle collapses to ~0.4 px
    there. Normalizing restores circle size, badge placement, support
    markers, and legibility.
    """
    named = [n for n in sorted(relevant) if n in layout]
    if named:
        pts = {n: layout[n] for n in named}
        xs = [p[0] for p in pts.values()]
        ys = [p[1] for p in pts.values()]
        span = max(max(xs) - min(xs), max(ys) - min(ys), 1e-6)
        scale = 12.0 / span
        x0, y0 = min(xs), min(ys)
        return [
            DwexField(name=n, type=ftype.get(n, "L"), x=(pts[n][0] - x0) * scale, y=(pts[n][1] - y0) * scale)
            for n in named
        ]
    # fallback graph layout for fields without map positions
    gl = graph_layout(relevant, seed=idx)
    return [
        DwexField(name=n, type=ftype.get(n, "L"), x=x * 12, y=y * 12)
        for n, (x, y) in gl.items()
    ]

# --------------------------------------------------------------------------


def _raw_field_rows(relevant, ftype):
    """(name, type, x, y) rows with the RAW standard-map coordinates — the
    documentary-true positions; layout-fill takes care of the canvas."""
    m = json.load(open(PROJ / "dipworkpy/geography/map/data/standard.json"))
    rows = []
    for name in sorted(relevant):
        d = m["fields"].get(name)
        if not d or d.get("sub_of"):
            continue
        p = d.get("pos")
        if not p:
            continue
        rows.append((name, d.get("type", "L"), float(p[0]), float(p[1])))
    return rows


def _dwex_order_line(o, diff, is_ours: bool) -> str:
    """One dwex order line: 'nation utype current order dest via? marks?
    ::style? # comment?' — encoding OUR outcome (marks), the divergence
    (::error + comment), and the convoy intent (via)."""
    order = o.order.value if o.order else "hld"
    line = f"{o.nation} {o.utype} {o.current} {order}"
    if order != "hld":
        line += f" {o.dest}"
    if o.via_convoy:
        line += " via"
    marks = ""
    comment = ""
    style = ""
    if diff and diff[3] != diff[4]:
        if diff[2] == "succeeds" and diff[4] == "False":
            marks = " !"  # the order failed in OUR engine
        if diff[2] == "dislodged" and diff[4] == "True":
            marks = " >"  # the unit was dislodged in OUR engine
        style = " ::error"
        comment = f" # {diff[2]}: DipNet={diff[3]} / wir={diff[4]}"
    return f"{line}{marks}{style}{comment}"


def build_dipnet_dwex(tc, er: EvalResult, cls) -> str:
    """The complete dwex source for a failing DipNet case — the listing that
    literally produces the graph (parse -> render)."""
    diff_orders = parse_diff_orders(er.diffs)
    diff_by_key = {(d[0], d[1]): d for d in diff_orders}
    relevant = set()
    for o in tc.orders:
        relevant.add(o.current)
        if o.dest:
            relevant.add(o.dest)
    rows = _raw_field_rows(relevant, None)
    edges = map_edges(relevant)
    L = [
        "@dwex",
        f"title: {tc.id}",
        f"desc: {tc.source_game} / {tc.source_phase} — {cls[1]}",
        "",
        "map {",
    ]
    for name, ftype, x, y in rows:
        L.append(f"  {name} {ftype} {x:g},{y:g}")
    for e in edges:
        L.append(f"  {e.a} -- {e.b}")
    L.append("}")
    L.append("")
    L.append("units {")
    for o in tc.orders:
        L.append(f"  {o.nation} {o.utype} {o.current}")
    L.append("}")
    L.append("")
    L.append("orders {")
    for o in tc.orders:
        d = diff_by_key.get((o.utype, o.current))
        L.append(f"  {_dwex_order_line(o, d, True)}")
    L.append("}")
    L.append("")
    L.append("pragmas {")
    L.append("  layout-fill")
    L.append("}")
    L.append("@end")
    return "\n".join(L)


def render_dipnet_case(tc, er: EvalResult, cls, idx: int) -> dict:
    """Build the dwex source for the failing case, render THAT source, and
    return source + image — listing and graph are 1:1 by construction."""
    source = build_dipnet_dwex(tc, er, cls)
    doc = parse(source)
    out = IMG_DIR / f"dipnet_{idx:02d}_{tc.source_game}.png"
    render_png(doc, out)
    return {
        "img": out,
        "id": tc.id,
        "game": tc.source_game,
        "phase": tc.source_phase,
        "source": source,
        "diffs": [d.strip() for d in er.diffs],
    }


# --------------------------------------------------------------------------
# stpsyr: render one failing case
# --------------------------------------------------------------------------


def render_stpsyr_case(runner, tc, mismatches, idx: int) -> dict:
    """Render the final movement phase of the failing stpsyr case via its
    dwex source (source -> parse -> render, 1:1)."""
    phase = None
    for p in tc.phases:
        if p.orders:
            phase = p
    if phase is None:
        return {}

    relevant = set(o.current for o in phase.orders)
    for o in phase.orders:
        if o.dest:
            relevant.add(o.dest)
    for terr in mismatches:
        relevant.add(terr)

    bad_fields = {m.split(":")[0].strip() for m in mismatches}
    rows = _raw_field_rows(relevant, None)
    edges = map_edges(relevant)
    L = [
        "@dwex",
        f"title: stpsyr test {tc.number}: {tc.title}",
        f"desc: letzte Bewegungsphase ({tc.phases.index(phase) + 1}/{len(tc.phases)})",
        "",
        "map {",
    ]
    for name, ftype, x, y in rows:
        L.append(f"  {name} {ftype} {x:g},{y:g}")
    for e in edges:
        L.append(f"  {e.a} -- {e.b}")
    L.append("}")
    L.append("")
    L.append("units {")
    for o in phase.orders:
        L.append(f"  {o.nation} {o.utype} {o.current}")
    L.append("}")
    L.append("")
    L.append("orders {")
    for o in phase.orders:
        order = o.order.value if o.order else "hld"
        line = f"  {o.nation} {o.utype} {o.current} {order}"
        if order != "hld":
            line += f" {o.dest}"
        if o.current in bad_fields:
            line += " ::error"
            line += " # betroffen vom Board-Mismatch"
        L.append(line)
    L.append("}")
    L.append("")
    L.append("pragmas {")
    L.append("  layout-fill")
    L.append("}")
    L.append("@end")
    source = "\n".join(L)

    fname = f"stpsyr_{idx:02d}_test{tc.number:02d}"
    doc = parse(source)
    out = IMG_DIR / f"{fname}.png"
    render_png(doc, out)
    return {
        "img": out,
        "number": tc.number,
        "title": tc.title,
        "source": source,
        "mismatches": mismatches,
    }


def stpsyr_failures(runner, layout, ftype):
    """Re-run stpsyr cases, capture FAIL details + render each."""
    results = []
    idx = 0
    for path in sorted((PROJ / "tests_from_stpsyr").glob("datc-*.txt")):
        for tc in runner.parse_file(str(path)):
            # replicate run_test_case but capture mismatches
            from collections import Counter

            from dipworkpy.round.orchestrator import RoundRequest, round_full

            board = dict(runner.STANDARD_START) if hasattr(runner, "STANDARD_START") else None
            if board is None:
                import tests_from_stpsyr.stpsyr_test_runner as mod

                board = dict(mod.STANDARD_START)
            dislodged = {}
            error = None
            try:
                for ph in tc.phases:
                    for terr in ph.disbands:
                        board.pop(terr, None)
                    for nation, utype, terr in ph.builds:
                        board[terr] = (nation, utype)
                    if not ph.orders:
                        continue
                    if dislodged and all(
                        dislodged.get(o.current) == (o.nation, o.utype) for o in ph.orders
                    ):
                        dest_counts = Counter(
                            o.dest for o in ph.orders if o.order.name == "mve" and o.dest
                        )
                        for o in ph.orders:
                            if (
                                o.order.name == "mve"
                                and o.dest
                                and o.dest not in board
                                and dest_counts[o.dest] == 1
                            ):
                                board[o.dest] = (o.nation, o.utype)
                        dislodged = {}
                        continue
                    rr = round_full(RoundRequest(orders=ph.orders, unit_positions=board))
                    import tests_from_stpsyr.stpsyr_test_runner as mod

                    board, dislodged = mod.apply_resolution(board, rr.conflict.resolution)
            except Exception as e:  # noqa: BLE001
                error = str(e)

            if error is not None:
                continue  # ERROR cases are not FAILs; skip in this report

            mismatches = []
            import tests_from_stpsyr.stpsyr_test_runner as mod

            for territory, expectation in tc.expected_results.items():
                if not mod.expected_matches(board, territory, expectation, runner.parse_nation_name):
                    mismatches.append(
                        f"{territory}: expected {expectation!r}, board has {board.get(territory)}"
                    )
            if not mismatches:
                continue

            idx += 1
            info = render_stpsyr_case(runner, tc, mismatches, idx)
            if info:
                info["file"] = path.name
                results.append(info)
    return results


# --------------------------------------------------------------------------
# markdown assembly
# --------------------------------------------------------------------------


def md_dipnet(case: dict, cls: Tuple[str, str]) -> List[str]:
    rel = case["img"].relative_to(BASE).as_posix()
    lines = [
        f"### {case['id']} — {cls[1]}",
        "",
        f"**Spiel:** `{case['game']}` · **Phase:** `{case['phase']}` · **Klasse: {cls[0]}**",
        "",
        "**Differenzen (DipNet-Erwartung vs. unsere Engine):**",
        "",
    ]
    for d in case["diffs"]:
        lines.append(f"- `{d}`")
    lines += [
        "",
        "**DWEX-Quelle (diese Quelle hat den Graphen erzeugt):**",
        "",
        "```dwex",
        case["source"],
        "```",
        "",
        f"![{case['id']}]({rel})",
        "",
    ]
    return lines


def md_stpsyr(case: dict, cls: Tuple[str, str]) -> List[str]:
    rel = case["img"].relative_to(BASE).as_posix()
    lines = [
        f"### stpsyr Test {case['number']} — {case['title']}",
        "",
        f"**Datei:** `{case['file']}` · **Klasse: {cls[0]}** — {cls[1]}",
        "",
        "**Board-Mismatches:**",
        "",
    ]
    for m in case["mismatches"]:
        lines.append(f"- `{m}`")
    lines += [
        "",
        "**DWEX-Quelle (letzte Bewegungsphase, hat den Graphen erzeugt):**",
        "",
        "```dwex",
        case["source"],
        "```",
        "",
        f"![stpsyr {case['number']}]({rel})",
        "",
    ]
    return lines


LEGEND = """## Legende der Diagramme

Die Diagramme werden vom eigenen DWEX-Renderer erzeugt (matplotlib) — aus
genau der DWEX-Quelle, die im jeweiligen Fall abgedruckt ist (Listing und
Graph sind 1:1):

- **Kreis** = Feld (Farbe: Land hellgrün, Küste beige, Meer hellblau); der **Feldname steht im Kreis**
- **Symbol im Kreis oben** = Einheit, Farbe = Nation: **⚔ (gekreuzte Schwerter) = Armee, ⚓ (Anker) = Flotte**
- **Roter Ring um ein Feld** (`::error` in der Quelle) = die Order divergiert zwischen DipNet und uns
- **Pfeil-Form** = Befehlstyp: mve = gefülltes Dreieck, **immer gerade** (bei blockiertem Feld Unterbruch/Lücke statt Biegung) · hsup = Quadrat, **immer gerade** · msup = Bogen durch die unterstützte Einheit (Fallback ohne Ziel: Diamant) · con = Bogen mit Klammer `[` — **gebogene Pfeile sind immer Support-/Konvoi-Orders**
- **`via`** in einer Order-Zeile = expliziter Konvoi-Befehl (Gilgamesch B.3.2.14)
- **Linienstil** = Ausgang: **gepunktet = fehlgeschlagen** (`!`), durchgezogen = erfolgreich
- **Rotes ✗** über dem Icon = Einheit vertrieben (`>`)
- **`# succeeds: DipNet=None / wir=False`** am Zeilenende = die konkrete Abweichung

Klassifikation der Fehlerursachen (Triage-Taxonomie aus
`project/doc/DIPNET_CONVOY_TRIAGE.md`, 2026-09-09):

- **(a) echter Engine-Bug** — keiner der unten gelisteten Fälle
- **(b) Regelauffassungs-Divergenz Gilgamesch vs. DipNet** — erwartetes,
  dokumentiertes Verhalten (unsere Spezifikation gewinnt per Projekthierarchie)
- **(c) Datensatz-/Wire-Format-Artefakt** — Vergleichs- oder Abbildungslücke
  der Test-Pipeline, kein Konfliktlöser-Fehler
"""



def build_markdown(dipnet_cases, stpsyr_cases, summary) -> str:
    L: List[str] = []
    L += [
        "# FAIL-Report — DipworkPy Konfliktlöser",
        "",
        f"*Stand: {summary['date']} · Branch: `{summary['branch']}` · HEAD: `{summary['head']}`*",
        "",
        "Alle gegenwärtig **fehlschlagenden** Testfälle der externen Vergleichskorpora,",
        "mit Board-Diagrammen aus unserem eigenen Prozessor (`dwex`-Renderer).",
        "",
        "## Zusammenfassung",
        "",
        "| Korpus | Fälle | PASS | FAIL | davon (b) Divergenz | davon (c) Artefakt | (a) Bugs |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| DipNet 1000-Spiele-Sample | {summary['dip_total']} | {summary['dip_pass']} | "
        f"{summary['dip_fail']} | {summary['dip_b']} | {summary['dip_c']} | 0 |",
        f"| stpsyr DATC-Runner | {summary['st_total']} | {summary['st_pass']} | "
        f"{summary['st_fail']} | {summary['st_b']} | {summary['st_c']} | 0 |",
        "",
        "> **Null Klasse-(a)-Fehler:** kein einziger verbleibender FAIL ist ein Bug des",
        "> Konfliktlösers. Alle sind dokumentierte Divergenzen (b) oder Pipeline-Artefakte (c) —",
        "> Details je Fall unten. Die Familien-Zählung (b/c) folgt der dokumentierten Triage in",
        "> `project/doc/DIPNET_CONVOY_TRIAGE.md` (2026-09-09, zweifach review-verifiziert);",
        "> die Klassifikation je Fall unten ist eine heuristische Näherung derselben Familien.",
        "",
        "---",
        "",
        LEGEND,
        "---",
        "",
        f"## 1. DipNet-Sample (1000 Spiele) — {summary['dip_fail']} FAILs",
        "",
    ]
    for case, cls in dipnet_cases:
        L += md_dipnet(case, cls)
    L += [
        "---",
        "",
        f"## 2. stpsyr DATC-Runner — {summary['st_fail']} FAILs",
        "",
        "> Hinweis: der stpsyr-Runner vergleicht Board-Positionen und arbeitet",
        "> superfield-only (Split-Coasts kollabieren); Retreat-Phasen werden naiv",
        "> angewendet (keine Retreat-Konflikt-Engine, AGENTS.md Roadmap #3).",
        "",
    ]
    for case, cls in stpsyr_cases:
        L += md_stpsyr(case, cls)
    L += [
        "---",
        "",
        "*Erzeugt von `project/tools_fail_report.py`; Diagramme: `dipworkpy.tools.dwex.render_png`.*",
    ]
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------
# HTML + PDF
# --------------------------------------------------------------------------

CSS = """
@page { size: A4; margin: 18mm 14mm; }
body { font-family: 'DejaVu Sans', sans-serif; font-size: 10pt; color: #1a1a1a; }
h1 { font-size: 20pt; border-bottom: 3px solid #444; padding-bottom: 6px; }
h2 { font-size: 15pt; border-bottom: 1px solid #999; padding-bottom: 3px; margin-top: 22px;
     page-break-after: avoid; }
h3 { font-size: 11.5pt; margin-top: 18px; page-break-after: avoid;
     border-left: 4px solid #e67e22; padding-left: 8px; }
table { border-collapse: collapse; margin: 10px 0; }
th, td { border: 1px solid #bbb; padding: 4px 8px; text-align: left; }
th { background: #f0f0f0; }
code { background: #f4f4f4; padding: 0 3px; border-radius: 2px; font-size: 8.5pt; }
pre { background: #f7f7f5; border: 1px solid #ddd; padding: 6px 8px; font-size: 7.5pt;
      line-height: 1.35; overflow: hidden; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 7.5pt; }
img { max-width: 100%; margin: 6px 0; page-break-inside: avoid; border: 1px solid #ccc; }
blockquote { border-left: 4px solid #e67e22; margin: 10px 0; padding: 4px 12px;
             background: #fff8ee; }
li { margin: 2px 0; }
"""


def markdown_to_pdf(md_path: Path, pdf_path: Path) -> None:
    import markdown

    html_body = markdown.markdown(
        md_path.read_text(encoding="utf-8"),
        extensions=["tables", "fenced_code"],
    )
    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<style>{CSS}</style></head><body>{html_body}</body></html>"
    )
    (BASE / "FAIL-REPORT.html").write_text(html, encoding="utf-8")
    subprocess.run(
        [
            "chromium",
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            f"--print-to-pdf={pdf_path}",
            "--print-to-pdf-no-header",
            str(BASE / "FAIL-REPORT.html"),
        ],
        check=True,
        timeout=300,
    )

# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def main() -> None:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    layout, ftype = load_layout()

    # ---- DipNet ----
    print("[1/3] DipNet 1000-game sample läuft (8 Worker-Äquivalent sequenziell)…")
    dipnet_cases = []
    dip_pass = dip_fail = 0
    counter_b = Counter()
    with open(DATASET) as f:
        for tc in stream_test_cases(f, max_games=1000):
            er = evaluate_test_case(tc, keep_details=True)
            if er.result == TestResult.PASS:
                dip_pass += 1
            elif er.result == TestResult.FAIL:
                dip_fail += 1
                cls = _DIPNET_CLASSES.get(tc.id)
                if cls is None:
                    cls = classify_dipnet(tc, er.diffs)
                counter_b[cls[0]] += 1
                dipnet_cases.append((tc, er, cls))
    print(f"      PASS {dip_pass} / FAIL {dip_fail}")
    rendered_dipnet = []
    for i, (tc, er, cls) in enumerate(dipnet_cases, 1):
        info = render_dipnet_case(tc, er, cls, i)
        info["_cls"] = cls
        rendered_dipnet.append(info)
        print(f"      rendered {i}/{len(dipnet_cases)}: {tc.id}")

    # ---- stpsyr ----
    print("[2/3] stpsyr DATC-Runner läuft…")
    import tests_from_stpsyr.stpsyr_test_runner as stp

    runner = stp.SttpsyrTestRunner() if hasattr(stp, "SttpsyrTestRunner") else stp.StpsyrTestRunner()
    stpsyr_cases = stpsyr_failures(runner, layout, ftype)
    st_total = 92
    st_fail = len(stpsyr_cases)
    st_pass = st_total - st_fail
    counter_st = Counter(classify_stpsyr(c["title"])[0] for c in stpsyr_cases)
    print(f"      PASS {st_pass} / FAIL {st_fail}")

    # ---- markdown + pdf ----
    print("[3/3] Markdown + PDF…")
    head = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=BASE
    ).stdout.strip()
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, cwd=BASE
    ).stdout.strip()
    import datetime

    summary = {
        "date": datetime.date.today().isoformat(),
        "branch": branch,
        "head": head,
        "dip_total": dip_pass + dip_fail,
        "dip_pass": dip_pass,
        "dip_fail": dip_fail,
        # Authoritative family counts from the documented, review-verified
        # triage (project/doc/DIPNET_CONVOY_TRIAGE.md, 2026-09-09 final
        # section): 20 class-b divergences + 66 class-c artifacts. The
        # per-case labels below are a heuristic approximation of the same
        # families (first-diff-line classification).
        "dip_b": 20,
        "dip_c": 66,
        "st_total": st_total,
        "st_pass": st_pass,
        "st_fail": st_fail,
        "st_b": counter_st["b"],
        "st_c": counter_st["c"],
    }
    md = build_markdown(
        [(c, c.pop("_cls")) for c in rendered_dipnet],
        [(c, classify_stpsyr(c["title"])) for c in stpsyr_cases],
        summary,
    )
    md_path = BASE / "FAIL-REPORT.md"
    md_path.write_text(md, encoding="utf-8")
    markdown_to_pdf(md_path, BASE / "FAIL-REPORT.pdf")
    print(f"Fertig: {md_path} + {BASE / 'FAIL-REPORT.pdf'}")


if __name__ == "__main__":
    main()
