"""DDL CLI: render, render-all, validate, to-json."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dipworkpy.tools.dwex.lang import parse_file
from dipworkpy.tools.dwex.render_png import render_png
from dipworkpy.tools.dwex.to_situation import to_situation, to_expected


def cmd_render(args: argparse.Namespace) -> int:
    doc = parse_file(args.path)
    out = args.path.with_suffix(".png")
    render_png(doc, out)
    print(f"rendered {out}")
    return 0


def cmd_render_all(args: argparse.Namespace) -> int:
    count = 0
    for p in sorted(args.dir.rglob("*.dwex")):
        doc = parse_file(p)
        out = p.with_suffix(".png")
        render_png(doc, out)
        print(f"rendered {out}")
        count += 1
    print(f"{count} files rendered")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    from dipworkpy.conflict_game import conflict_game
    doc = parse_file(args.path)
    sit = to_situation(doc)
    expected = to_expected(doc)
    result = conflict_game(sit)
    ok = result <= expected
    print(f"{'PASS' if ok else 'FAIL'} {args.path}")
    return 0 if ok else 1


def cmd_to_json(args: argparse.Namespace) -> int:
    doc = parse_file(args.path)
    sit = to_situation(doc)
    print(sit.model_dump_json(indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser("dwex")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render")
    r.add_argument("path", type=Path)
    r.set_defaults(fn=cmd_render)

    a = sub.add_parser("render-all")
    a.add_argument("dir", type=Path)
    a.set_defaults(fn=cmd_render_all)

    v = sub.add_parser("validate")
    v.add_argument("path", type=Path)
    v.set_defaults(fn=cmd_validate)

    j = sub.add_parser("to-json")
    j.add_argument("path", type=Path)
    j.set_defaults(fn=cmd_to_json)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
