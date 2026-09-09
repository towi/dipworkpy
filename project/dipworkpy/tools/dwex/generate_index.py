"""Generate doc/EXAMPLES.md from all .dwex files."""

from __future__ import annotations

import sys
from pathlib import Path

from dipworkpy.tools.dwex.lang import parse_file


def generate(dwex_dir: Path, out: Path) -> None:
    lines = [
        "# DDL Examples",
        "",
        "## DWEX in 60 seconds",
        "",
        "DWEX (`.dwex`) is the tiny source language behind these executable diagrams.",
        "Each file starts with `@dwex`, ends with `@end`, declares an inline `map { ... }`,",
        "and usually lists executable `orders { ... }`. Order result markers are part of",
        "the expected regression result: `!` means failed, `>` means dislodged, and `!>` means both.",
        "",
        "Prefer canonical field names from the standard map / FIELDS data: use `ENG` for",
        "English Channel, not legacy aliases such as `CHN`. Artificial names such as `ZZZ`",
        "are reserved for examples that intentionally demonstrate invalid input.",
        "",
        "See [DWEX-language.md](DWEX-language.md) for the full language reference.",
        "",
    ]
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
