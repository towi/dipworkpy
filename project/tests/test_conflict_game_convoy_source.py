"""cmove promotion follows ConvoyGraph.cmove_candidates when a graph is present."""

from dipworkpy.conflict_game import conflict_game, parser
from dipworkpy.eval.eval_model import t_order
from dipworkpy.geography.model import GeographyRequest
from dipworkpy.geography.service import geography_phase
from dipworkpy.model import Order, OrderType, Situation


def mko(nation, utype, current, order, dest=None):
    return Order(nation=nation, utype=utype, current=current, order=order, dest=dest)


def _world_with_geography(orders):
    geo = geography_phase(GeographyRequest(orders=orders))
    return parser(
        Situation(orders=geo.orders),
        order_geo_info=geo.order_geo_info,
        convoy_graph=geo.convoy_graph,
    )


def test_promotion_follows_cmove_candidates_only():
    """Fleet Nap->Apu 'convoyed' by ION: ION borders BOTH Nap and Apu,
    so the con order itself classifies valid and survives as
    t_order.convoy — but fleets are not convoyable (GEO-009 excludes
    them from cmove_candidates). Old parser: the con-scan promotes the
    fleet move to cmove (RED). New parser: candidates are authoritative,
    the move stays nmove (GREEN)."""
    world = _world_with_geography(
        [
            mko("It", "F", "Nap", OrderType.mve, "Apu"),
            mko("It", "F", "ION", OrderType.con, "Nap"),
        ]
    )
    assert world.get_field("Nap").order == t_order.nmove, world.get_field("Nap")


def test_real_convoy_is_promoted():
    world = _world_with_geography(
        [
            mko("En", "A", "Lon", OrderType.mve, "Nor"),
            mko("En", "F", "NTH", OrderType.con, "Lon"),
        ]
    )
    assert world.get_field("Lon").order == t_order.cmove, world.get_field("Lon")


def test_legacy_no_graph_path_unchanged():
    world = parser(
        Situation(
            orders=[
                mko("En", "A", "Lon", OrderType.mve, "Nor"),
                mko("En", "F", "NTH", OrderType.con, "Lon"),
            ]
        )
    )
    assert world.get_field("Lon").order == t_order.cmove, world.get_field("Lon")


def test_end_to_end_valid_convoy_succeeds():
    orders = [
        mko("En", "A", "Lon", OrderType.mve, "Nor"),
        mko("En", "F", "NTH", OrderType.con, "Lon"),
    ]
    geo = geography_phase(GeographyRequest(orders=orders))
    cr = conflict_game(Situation(orders=geo.orders), order_geo_info=geo.order_geo_info, convoy_graph=geo.convoy_graph)
    lon = next(o for o in cr.orders if o.current == "Lon")
    assert lon.succeeds is None, cr
