from pathlib import Path

DOC_ROOT = Path(__file__).resolve().parent.parent / "doc"


def test_dwex_language_reference_exists_and_is_linked() -> None:
    language = DOC_ROOT / "DWEX-language.md"
    assert language.exists()

    examples = (DOC_ROOT / "EXAMPLES.md").read_text()
    index = (DOC_ROOT / "index.md").read_text()
    readme = (DOC_ROOT / "README.md").read_text()

    assert "[DWEX-language.md](DWEX-language.md)" in examples
    assert "[DWEX-language.md](DWEX-language.md)" in index
    assert "[DWEX-language.md](DWEX-language.md)" in readme


def test_examples_start_with_short_dwex_language_summary() -> None:
    examples = (DOC_ROOT / "EXAMPLES.md").read_text()
    summary = examples.split("## 01", 1)[0]

    assert "## DWEX in 60 seconds" in summary
    assert "@dwex" in summary
    assert "map {" in summary
    assert "orders {" in summary
    assert "ENG" in summary
    assert "CHN" in summary
