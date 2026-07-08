from dipworkpy.tools.dwex.model import (
    DwexDocument,
    DwexField,
    DwexEdge,
    DwexOrderSpec,
)


def test_minimal_document():
    doc = DwexDocument(
        title="t",
        description="",
        fields=[DwexField(name="A", type="LA", x=0, y=0)],
        edges=[],
        units=[],
        orders=[],
    )
    assert doc.title == "t"


def test_edge_default_passability():
    e = DwexEdge(a="A", b="B")
    assert e.army == "ja"
    assert e.fleet == "ja"
    assert e.convoy_move == "ja"


def test_edge_army_only():
    e = DwexEdge(a="A", b="B", army="ja", fleet="nein", convoy_move="nein")
    assert e.fleet == "nein"


def test_order_spec_failure_marker():
    o = DwexOrderSpec(
        nation="Au",
        utype="A",
        current="Vie",
        order="mve",
        dest="Tyr",
        expected_failed=True,
    )
    assert o.expected_failed is True
