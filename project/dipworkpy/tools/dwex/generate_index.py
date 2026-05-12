"""Generate doc/EXAMPLES.md from all .dwex files."""
from __future__ import annotations

import sys
from pathlib import Path

from dipworkpy.tools.dwex.lang import parse_file


def generate(dwex_dir: Path, out: Path) -> None:
    lines = ["# DDL Examples", ""]
    for p in sorted(dwex_dir.rglob("*.dwex")):
        doc = parse_file(p)
        png_rel = p.with_suffix(".png").relative_to(out.parent)
        lines.append(f"## {doc.title}")
        lines.append("")
        if doc.description:
            lines.append(doc.description)
            lines.append("")
        lines.append(f"![{doc.title}]({png_rel})")
        lines.append("")
        lines.append("<details><summary>DDL source</summary>")
        lines.append("")
        lines.append("```")
        lines.append(p.read_text())
        lines.append("```")
        lines.append("</details>")
        lines.append("")
    out.write_text("\n".join(lines))


if __name__ == "__main__":
    generate(Path(sys.argv[1]), Path(sys.argv[2]))
