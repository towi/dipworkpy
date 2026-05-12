import pytest
from pydantic import ValidationError
from dipworkpy.diag import Diagnostic


def test_diagnostic_minimal():
    d = Diagnostic(phase="geography", rule="GEO-001", severity="info",
                   message="ok")
    assert d.phase == "geography"
    assert d.order_index is None
    assert d.details == {}


def test_diagnostic_with_order_index_and_details():
    d = Diagnostic(
        phase="syntax", rule="SYN-005", severity="correction",
        order_index=3, message="double order on Vie",
        details={"existing": "mve Mun", "incoming": "hld"},
    )
    assert d.order_index == 3
    assert d.details["existing"] == "mve Mun"


def test_diagnostic_rejects_unknown_phase():
    with pytest.raises(ValidationError):
        Diagnostic(phase="magic", rule="X", severity="info", message="")


def test_diagnostic_rejects_unknown_severity():
    with pytest.raises(ValidationError):
        Diagnostic(phase="syntax", rule="X", severity="boom", message="")
