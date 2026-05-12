from pathlib import Path
from dipworkpy.tools.dwex.lang import parse
from dipworkpy.tools.dwex.render_png import render_png

DOC = """
@dwex
title: Smoke test
map {
  A LA 0,0
  B LA 1,0
  A -- B
}
orders {
  Au A A mve B
}
@end
"""


def test_render_writes_png(tmp_path: Path):
    doc = parse(DOC)
    out = tmp_path / "smoke.png"
    render_png(doc, out)
    assert out.exists()
    assert out.stat().st_size > 1000  # non-trivial PNG
    # PNG magic bytes
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
