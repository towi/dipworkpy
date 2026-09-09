"""
While writing these tests I noticed a discrepancy about default values and optional values
between t_field and OrderResult, especially around "succeeds" and "dislodged".
I may have to clean that up later. Remember that the intent of t_field is to be used internally
and default may hinder clean coding, while OrderResult is a visible output and a simple style is useful.
"""

# local
from dipworkpy import model
from dipworkpy.eval.eval_model import t_world, t_field, t_order

# under test
from dipworkpy.conflict_game import writer, conflict_game
from dipworkpy.round.orchestrator import RoundRequest, round_full

################################################


def mk_field(s: str) -> t_field:
    """@:param s -- field description to parse, eg "Ge A Vie", "Ge A Vie nmove Mun", "Ge A Vie msupport Mun".
    Add an "!" and/or an "<" (separated by spaces) to mark the field as "not succeeded" or "disbanded".
    The order type is the long notatation from t_field, ie. "msupport" instead of "msup".
    The unit type in the field description is almost ignored (because it doesnt matter for conflict resolution where
    fields are considered), you can use "A" or "F" or "?". To set the a strength use "1" or "2", etc.
    """
    all_toks = s.strip().split()
    toks = [tok for tok in all_toks if tok not in {"!", "<"}]
    pl, utype, nm = toks[0:3]
    strength: int = 1 if utype in {"A", "F"} else int(utype)  # "A", "F" or "1", or "2", etc.
    succeeds: bool = "!" not in all_toks
    dislodged: bool = "<" in all_toks
    if len(toks) == 3:  # "Au A Vie"
        return t_field(
            player=pl,
            order=t_order.none,
            dest=nm,
            xref=nm,
            strength=strength,
            name=nm,
            succeeds=succeeds,
            dislodged=dislodged,
        )
    elif len(toks) == 4:  # "Au A Vie hld"
        return t_field(
            player=pl,
            order=t_order(all_toks[3]),
            dest=nm,
            xref=nm,
            strength=strength,
            name=nm,
            succeeds=succeeds,
            dislodged=dislodged,
        )
    elif len(toks) == 5:  # "Au A Vie mve Mun"
        return t_field(
            player=pl,
            order=t_order(all_toks[3]),
            dest=all_toks[4],
            xref=all_toks[4],
            strength=strength,
            name=nm,
            succeeds=succeeds,
            dislodged=dislodged,
        )
    else:
        raise Exception("error")


################################################


def mk_oresult(s: str) -> model.OrderResult:
    """@:param s -- order description to parse, eg "Ge A Vie", "Ge A Vie mve Mun", "Ge A Vie msup Mun".
    Add an "!" and/or an "<" (separated by spaces) to mark the field as "not succeeded" or "disbanded".
    The order type is the short notatation from OrderResult, ie. "msup" instead of "msupport".
    TODO The unit type is currently ignored and set to "?", I do not pass the original info down yet.
    """
    toks = s.split()
    n, u, c, o, d = toks[0:5]
    succeeds = None if "!" not in toks else False
    dislodged = None if "<" not in toks else True
    return model.OrderResult(nation=n, utype="?", current=c, order=o, dest=d, succeeds=succeeds, dislodged=dislodged)


################################################


def test_t_field_model():
    f = t_field(player="En", order=t_order.none, dest="NTH", xref="NTH", strength=1, name="NTH")
    assert f.name == "NTH"


def test_mk_field():
    res = mk_field("Au A Vie")
    exp = t_field(player="Au", order=t_order.none, dest="Vie", xref="Vie", strength=1, name="Vie")
    assert res == exp


def test_mk_oresult():
    assert mk_oresult("Au A Vie hld Vie") == model.OrderResult(
        nation="Au", utype="?", current="Vie", order="hld", dest="Vie", succeeds=None, dislodged=None
    )
    assert mk_oresult("Ge A Mun hld Vie !") == model.OrderResult(
        nation="Ge", utype="?", current="Mun", order="hld", dest="Vie", succeeds=False, dislodged=None
    )


################################################


def test_writer_01():
    # arrange
    world: t_world = t_world(
        fields_={
            "Vie": mk_field("Au A Vie"),
        },
        switches={},
    )
    # act
    res = writer(world=world)
    # assert
    assert res.orders == [
        mk_oresult("Au ? Vie hld Vie"),
    ]
    assert res.pattfields == set()


def test_writer_02():
    # arrange
    world: t_world = t_world(
        fields_={
            "Vie": mk_field("Au A Vie"),
            "Mun": mk_field("Ge A Mun umove Vie !"),
            "NTH": mk_field("En 2 NTH"),
        },
        switches={},
    )
    # act
    res = writer(world=world)
    # assert
    assert res.orders == [
        mk_oresult("Au A Vie hld Vie"),
        mk_oresult("Ge A Mun hld Vie !"),
        mk_oresult("En 2 NTH hld NTH"),
    ]
    assert res.pattfields == set()


################################################


def test_writer_pattfields_01():
    # arrange
    world: t_world = t_world(
        fields_={
            "Vie": mk_field("Au A Vie umove Mun !"),
            "Kie": mk_field("Ge A Kie umove Mun !"),
        },
        switches={},
    )
    # act
    res = writer(world=world)
    # assert
    assert len(res.orders) == 2
    assert res.pattfields == {"Mun"}


def test_writer_pattfields_02():
    # arrange
    world: t_world = t_world(
        fields_={
            "Vie": mk_field("Au A Vie umove Mun !"),
            "Mun": mk_field("Ge A Mun"),
        },
        switches={},
    )
    # act
    res = writer(world=world)
    # assert
    assert len(res.orders) == 2
    assert res.pattfields == set()  # Mun is not a pattfield


def test_writer_pattfields_03():
    # arrange
    world: t_world = t_world(
        fields_={
            "Vie": mk_field("Au A Vie umove Mun !"),
            "Mun": mk_field("Ge A Mun"),
            "Kie": mk_field("Ge A Kie nmove Mun"),
            "Ber": mk_field("Ge A Ber msupport Kie"),
        },
        switches={},
    )
    # act
    res = writer(world=world)
    # assert
    assert len(res.orders) == 4
    assert res.pattfields == set()  # Mun is not a pattfield


################################################


def mk_con_field(s: str, army_start: str) -> t_field:
    """@:param s -- fleet field description with a convoy order, eg "En F ENG convoy Lon".
    @:param army_start -- start field of the convoyed army; sets the original con
    order (mk_field alone leaves original_order unset, but the writer reports
    convoy outcomes from t_field plus original_order).
    """
    f = mk_field(s)
    f.original_order = model.Order(
        nation=f.player, utype="F", current=f.name, order=model.OrderType.con, dest=army_start
    )
    return f


def _by_current(res) -> dict:
    return {o.current: o for o in res.orders}


def test_writer_con_order_executed_convoy_reports_success():
    # arrange: A Lon moved successfully via the ENG convoy
    world: t_world = t_world(
        fields_={
            "Lon": mk_field("En A Lon cmove Bre"),
            "ENG": mk_con_field("En F ENG convoy Lon", army_start="Lon"),
        },
        switches={},
    )
    # act
    res = writer(world=world)
    # assert
    con = _by_current(res)["ENG"]
    assert con.order == model.OrderType.con
    assert con.succeeds is None  # convoy executed -> default success


def test_writer_con_order_disrupted_convoy_reports_failure():
    # arrange: convoy disrupted, the army's move collapsed back to a hold
    world: t_world = t_world(
        fields_={
            "Lon": mk_field("En A Lon"),
            "ENG": mk_con_field("En F ENG convoy Lon", army_start="Lon"),
        },
        switches={},
    )
    # act
    res = writer(world=world)
    # assert
    con = _by_current(res)["ENG"]
    assert con.order == model.OrderType.con
    assert con.succeeds is False  # army is not a surviving cmove


def test_writer_con_order_without_companion_mve_reports_failure():
    # arrange: legacy conflict_game path (no geography): F NTH con Lon, but no
    # army is ordered to move from Lon (parser adds an empty Lon field).
    situation = model.Situation(
        orders=[
            model.Order(nation="En", utype="F", current="NTH", order=model.OrderType.con, dest="Lon"),
        ]
    )
    # act
    res = conflict_game(situation)
    # assert
    con = _by_current(res)["NTH"]
    assert con.order == model.OrderType.con
    assert con.succeeds is False  # no convoyed army -> convoy cannot execute


def test_writer_con_order_geo_invalid_reports_failure():
    # arrange: full round: A Lon mve Mun (no convoy route exists) + F ENG con Lon.
    # Geography rejects the con order under GEO-006 (ENG is on no route Lon->Mun),
    # so it collapses to a hold in the engine model.
    req = RoundRequest(
        orders=[
            model.Order(nation="En", utype="A", current="Lon", order=model.OrderType.mve, dest="Mun"),
            model.Order(nation="En", utype="F", current="ENG", order=model.OrderType.con, dest="Lon"),
        ],
        unit_positions={"Lon": ("En", "A"), "ENG": ("En", "F")},
    )
    # act
    res = round_full(req)
    # assert
    assert "GEO-006" in {d.rule for d in res.diagnostics}
    con = _by_current(res.conflict.resolution)["ENG"]
    assert con.order == model.OrderType.hld  # geo-invalid con collapsed to a hold
    assert con.succeeds is False  # ... so the convoy did not execute


################################################


if __name__ == "__main__":
    import sys
    import pytest

    pytest.main(sys.argv + ["-v"])
