# std py
from typing import Set
# 3rd level
# local
from .eval_model import t_order, t_field, t_world


def cut_supports(world: t_world, category:int, relevant_moves:Set[t_order]):
    _scok : bool = world.switches.self_cut_ok
    _pcp : int = world.switches.partial_cut_possible
    #
    field : t_field
    for field in world.get_fields(lambda f: f.order in relevant_moves):
        dest_field = world.get_field(field.dest)
        if not dest_field: continue
        if( # field.order in relevant_moves and
            dest_field.category == category and
            dest_field.order in { t_order.hsupport, t_order.msupport } and
            ((dest_field.player != field.player) or _scok)
        ):
            dest_field.support_strength -= field.strength
            field.add_event('$sup_dec')
            if (dest_field.support_strength <= 0) or (_pcp==0) or (_pcp==2 and field.strength>0):
                dest_field.support_strength = 0
                dest_field.order = t_order.none
                dest_field.add_event('$sup_cut')
            pass
        pass
    return


def count_supporters(world: t_world, category:int):
    # msupports
    for _field in world.get_fields(lambda f: f.category==category and f.order in {t_order.msupport}):
        field : t_field = _field
        j = field.xref
        dest_field = world.get_field(j)
        if not dest_field: continue
        dest_field.strength_a += field.support_strength
        if field.player != dest_field.player:
            dest_field.strength_b += field.strength_b
    # hsupports
    for _field in world.get_fields(lambda f: f.category==category and f.order in {t_order.hsupport}):
        field : t_field = _field
        j = field.xref
        dest_field = world.get_field(j)
        if not dest_field: continue
        dest_field.defensive_strength += field.support_strength
    return


def resolve_conflict_at_field(world : t_world, ffield : t_field):
    _ri93 = world.switches.rule_interpretation_IX_3
    if ffield.order in { None, t_order.cmove, t_order.nmove }:
        defval : int = 0
    else:
        defval : int = ffield.defensive_strength
    ffield.add_event("$C") # has conflict
    draw_a : bool = False
    draw_b : bool = False
    maxstrength_a : int = defval
    winner_a : t_field = ffield
    maxstrength_b : int = defval
    winner_b : t_field = ffield
    #
    ifield : t_field
    for ifield in world.get_fields(lambda i: i.order in { t_order.nmove, t_order.cmove }):
        if ifield.dest != ffield.name: continue
        ifield.add_event("$A") # attacks
        draw_a |= ifield.strength_a == maxstrength_a
        if ifield.strength_a > maxstrength_a:
            draw_a = False
            maxstrength_a = ifield.strength_a
            winner_a = ifield
        draw_b |= ifield.strength_b == maxstrength_b
        if ifield.strength_b > maxstrength_b:
            draw_b = False
            maxstrength_b = ifield.strength_b
            winner_b = ifield
        #_ if
    #_ for
    #
    if draw_a:
        winner_a = ffield
    if draw_b:
        winner_b = ffield
    #
    if defval > 0 and ffield.player==winner_a.player:
        winner_a = ffield
    #
    if winner_a != ffield and defval > 0:
        if _ri93 == 0:
            if winner_b == ffield: winner_a = ffield
        elif _ri93 == 1:
            if winner_b != winner_a: winner_a = ffield
        elif _ri93 == 2:
            if winner_a.strength_b <= defval: winner_a = ffield
        else:
            raise NameError(f"unknown rule_interpretation_IX_3:{_ri93}")
    #
    for ifield in world.get_fields(lambda i: i.order in {t_order.nmove, t_order.cmove}):
        if ifield.dest == ffield.name:
            ifield.succeeds = ifield == winner_a
            ifield.add_event(f"$win:{ifield.succeeds}")
    #
    return


def change_moves_to_umoves(world : t_world, category:int):
    for field in world.get_fields(
        lambda f:
            f.category == category and
            f.order in {t_order.cmove, t_order.nmove} and
            not f.succeeds
    ):
        field.order = t_order.umove
        field.add_event("$umove")
    return


def resolve_conflict_at_border(world : t_world, f1 : t_field, f2 : t_field):
    f1.succeeds = f1.strength_b > f2.strength_b
    f2.succeeds = f2.strength_b > f1.strength_b
    f1.add_event(f"$rcab:{f1.succeeds}={f1.strength_b}>{f2.strength_b}")
    f2.add_event(f"$rcab:{f2.succeeds}={f2.strength_b}>{f1.strength_b}")
