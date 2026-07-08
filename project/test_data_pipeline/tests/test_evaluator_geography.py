"""Regression tests: evaluator adjudicates convoys via geography and
feeds ORIGINAL orders to the engine (no void rewrite)."""

from dipworkpy.model import Order, OrderResult, OrderType

from test_data_pipeline.dipnet_parser import DwpcrTestCase
from test_data_pipeline.evaluator import TestResult, evaluate_test_case


def mko(nation, utype, current, order, dest=None):
    return Order(nation=nation, utype=utype, current=current, order=order, dest=dest)


def mkr(nation, utype, current, order, dest=None, succeeds=None, dislodged=None):
    return OrderResult(
        nation=nation, utype=utype, current=current, order=order, dest=dest, succeeds=succeeds, dislodged=dislodged
    )


def _case(case_id, orders, expected, has_convoy, void_indices=(), mismatch_indices=()):
    return DwpcrTestCase(
        id=case_id,
        orders=orders,
        expected=expected,
        has_convoy=has_convoy,
        has_void=bool(void_indices),
        source_phase="TEST",
        source_game="TEST",
        void_order_indices=list(void_indices),
        mismatch_support_indices=list(mismatch_indices),
    )


def test_broken_convoy_route_fails_the_move():
    """F ADR cannot convoy Lon->Nor. The legacy 'always' engine let any
    surviving convoyer validate the route; with geography the move must
    not succeed. Asserting PASS (not merely != INCONCLUSIVE, which
    becomes vacuous once the branch is deleted): the expected results
    encode the failed move, so PASS means the engine agrees."""
    tc = _case(
        "synthetic_convoy_broken",
        orders=[
            mko("En", "A", "Lon", OrderType.mve, "Nor"),
            mko("En", "F", "ADR", OrderType.con, "Lon"),
        ],
        expected=[
            mkr("En", "A", "Lon", OrderType.mve, "Nor", succeeds=False),
            mkr("En", "F", "ADR", OrderType.con, "Lon"),
        ],
        has_convoy=True,
    )
    result = evaluate_test_case(tc, keep_details=True)
    assert result.result == TestResult.PASS, (result.reason, result.diffs)


def test_valid_convoy_is_adjudicated_pass():
    """Characterization (passes before AND after): clean convoy PASSes."""
    tc = _case(
        "synthetic_convoy_ok",
        orders=[
            mko("En", "A", "Lon", OrderType.mve, "Nor"),
            mko("En", "F", "NTH", OrderType.con, "Lon"),
        ],
        expected=[
            mkr("En", "A", "Lon", OrderType.mve, "Nor"),
            mkr("En", "F", "NTH", OrderType.con, "Lon"),
        ],
        has_convoy=True,
    )
    result = evaluate_test_case(tc)
    assert result.result == TestResult.PASS, result


def test_void_support_still_bounces_third_party():
    """DipNet-void support (attack on own unit) keeps its bounce strength.

    Fr Ber->Mun (Kie+Ruh support, both dataset-void because Mun is
    French) vs Au Tyr->Mun (Boh support) while Fr Mun->Sil bounces:
    nothing may enter Mun and Mun must not be dislodged. With the old
    void->hld rewrite Tyr won Mun — that was DipNet FAIL _xh_i5Do.
    """
    orders = [
        mko("Au", "A", "Tyr", OrderType.mve, "Mun"),
        mko("Au", "A", "Boh", OrderType.msup, "Tyr"),
        mko("Fr", "A", "Ber", OrderType.mve, "Mun"),
        mko("Fr", "A", "Mun", OrderType.mve, "Sil"),
        mko("Fr", "A", "Kie", OrderType.msup, "Ber"),
        mko("Fr", "A", "Ruh", OrderType.msup, "Ber"),
        mko("Au", "A", "Sil", OrderType.hld),
    ]
    expected = [
        mkr("Au", "A", "Tyr", OrderType.mve, "Mun", succeeds=False),
        mkr("Au", "A", "Boh", OrderType.msup, "Tyr"),
        mkr("Fr", "A", "Ber", OrderType.mve, "Mun", succeeds=False),
        mkr("Fr", "A", "Mun", OrderType.mve, "Sil", succeeds=False),
        # Kie/Ruh are void-marked in the dataset: excluded via void_keys,
        # their expected entries are irrelevant but must exist.
        mkr("Fr", "A", "Kie", OrderType.msup, "Ber"),
        mkr("Fr", "A", "Ruh", OrderType.msup, "Ber"),
        mkr("Au", "A", "Sil", OrderType.hld),
    ]
    tc = _case("synthetic_void_support", orders, expected, has_convoy=False, void_indices=(4, 5))
    result = evaluate_test_case(tc)
    assert result.result == TestResult.PASS, result


def test_mismatch_hold_support_is_rewritten_not_live():
    """A hold-support on a unit that actually MOVES is dataset-void AND
    a statement mismatch -> rewritten to hld, so it must NOT protect
    the mover from dislodgement (round-2 regression class, 24 cases,
    e.g. -joCH1jONGKS0wBT_F1903M)."""
    orders = [
        mko("Au", "A", "Tyr", OrderType.mve, "Tri"),  # bounces on Tri
        mko("Ru", "A", "Tri", OrderType.hld),
        mko("It", "A", "Ven", OrderType.mve, "Tyr"),
        mko("It", "A", "Pie", OrderType.msup, "Ven"),
        mko("Ge", "A", "Mun", OrderType.hsup, "Tyr"),  # void+mismatch: Tyr moves
    ]
    expected = [
        mkr("Au", "A", "Tyr", OrderType.mve, "Tri", succeeds=False, dislodged=True),
        mkr("Ru", "A", "Tri", OrderType.hld),
        mkr("It", "A", "Ven", OrderType.mve, "Tyr"),
        mkr("It", "A", "Pie", OrderType.msup, "Ven"),
        mkr("Ge", "A", "Mun", OrderType.hsup, "Tyr"),  # void -> comparison-skipped
    ]
    tc = _case(
        "synthetic_mismatch_support", orders, expected, has_convoy=False, void_indices=(4,), mismatch_indices=(4,)
    )
    result = evaluate_test_case(tc, keep_details=True)
    assert result.result == TestResult.PASS, (result.reason, result.diffs)


def test_geo_invalid_move_compares_as_failed_move():
    """Engine demotes an illegal move to hld/succeeds=None (B.4.2.9);
    DipNet expects mve/succeeds=False. The comparison maps the two
    (round-2 regression class, 7 cases)."""
    tc = _case(
        "synthetic_invalid_move",
        orders=[mko("Tu", "A", "Con", OrderType.mve, "Seb")],
        expected=[mkr("Tu", "A", "Con", OrderType.mve, "Seb", succeeds=False)],
        has_convoy=False,
    )
    result = evaluate_test_case(tc, keep_details=True)
    assert result.result == TestResult.PASS, (result.reason, result.diffs)
