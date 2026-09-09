"""The two DipNet cases that failed while the evaluator rewrote void
orders to holds (fixed in the geography-wiring change). Pinned offline."""

import json
import os

import pytest

from dipworkpy.model import Order, OrderResult

from test_data_pipeline.dipnet_parser import DwpcrTestCase

# Alias the enum: an unaliased `TestResult` import makes pytest try to
# collect it as a test class (PytestCollectionWarning).
from test_data_pipeline.evaluator import TestResult as EvalVerdict
from test_data_pipeline.evaluator import evaluate_test_case

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.mark.parametrize(
    "case_id",
    [
        "1IbGdARWCes1lsqm_F1906M",
        "_xh_i5Do4jzgx8yS_F1906M",
    ],
)
def test_ex_fail_case_passes(case_id):
    with open(os.path.join(FIXTURES, case_id + ".json")) as f:
        raw = json.load(f)
    tc = DwpcrTestCase(
        id=raw["id"],
        orders=[Order(**o) for o in raw["orders"]],
        expected=[OrderResult(**r) for r in raw["expected"]],
        has_convoy=raw["has_convoy"],
        has_void=raw["has_void"],
        source_phase=raw["source_phase"],
        source_game=raw["source_game"],
        void_order_indices=raw["void_order_indices"],
        mismatch_support_indices=raw["mismatch_support_indices"],
    )
    result = evaluate_test_case(tc, keep_details=True)
    assert result.result == EvalVerdict.PASS, result.diffs
