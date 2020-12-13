"""
impl k2 phase
"""

# std py
# 3rd level
# local
from eval_model import t_order, t_field, t_world
import eval_common
from dipworkpy import debug

__ALL__ = [ "k2_evaluation" ]


###########################################################


def k2_evaluation(world: t_world):
    if debug: print('=== K2 ===')
    # prepare
    # - aliases for brevity
    hsupport, msupport, cmove, nmove, umove = t_order.hsupport, t_order.msupport, t_order.cmove, t_order.nmove, t_order.umove
    # - k2_relevant_moves
    k2_relevant_moves = { nmove }
    if world.switches.convoy_cuts:
        k2_relevant_moves.add(cmove)
    #
    # {mark k2 fields}
    ifield : t_field
    dest_field : t_field
    for ifield, dest_field in world.get_fields_dests(lambda f: f.order in { msupport }):
        if dest_field.order in k2_relevant_moves and dest_field.dest==ifield.name:
            ifield.fcategory = 2
            ifield.add_event('$k2f')
    # .. {it may seem to be wrong that no check is included, whether
    #   both units belong to different players, but this case does no harm}
    #
    # {mark k2 moves and supports}
    for ifield, dest_field in world.get_fields_dests(lambda f: f.order in { hsupport, msupport, cmove, nmove }):
        if dest_field.fcategory == 2:
            ifield.category = 2
            ifield.add_event('$k2c')
    eval_common.cut_supports(world, category=2, relevant_moves={cmove, nmove, umove})
    eval_common.count_supporters(world, category=2)
    #
    # {evaluate conflicts}
    for ifield in world.get_fields(lambda f: f.category==2):
        eval_common.resolve_conflict_at_field(world, ifield)
    #
    # {change unsuccessfull critical k2 moves to nops}
    for ifield, dest_field in world.get_fields_dests(lambda f: f.category==2 and f.order in k2_relevant_moves and not f.succeeds):
        if dest_field.order in {msupport} and dest_field.dest==ifield.name:
            ifield.order = t_order.none
            ifield.add_event("$ck2n")
    eval_common.change_moves_to_umoves(world, 2)
    #
    return


###########################################################
