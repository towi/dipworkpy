"""
impl k4 phase
"""

# std py
# 3rd level
# local

from dipworkpy.dip_eval.eval_model import t_order, t_field, t_world
import eval_common
from dipworkpy import debug

__ALL__ = [ "k4_evaluation" ]


###########################################################


def k4_evaluation(world: t_world):
    if debug: print('=== K4 ===')
    # prepare
    # - aliases for brevity
    hsupport, msupport, cmove, nmove, umove = t_order.hsupport, t_order.msupport, t_order.cmove, t_order.nmove, t_order.umove
    #
    # {mark k4 felds}
    ifield : t_field
    dest_field : t_field
    for ifield, dest_field in world.get_fields_dests(lambda f: f.order in { cmove, nmove, umove }):
        if dest_field.category==0:
            dest_field.fcategory = 4
            dest_field.add_event('$k4f')
    #
    # {mark k4 moves and supports}
    for ifield, dest_field in world.get_fields_dests(lambda f: f.order in { hsupport, msupport, cmove, nmove }):
        if dest_field.fcategory == 4:
            ifield.category = 4
            ifield.add_event('$k4c')
    eval_common.cut_supports(world, category=4, relevant_moves={cmove, nmove, umove})
    eval_common.count_supporters(world, category=4)
    #
    # units block each other in a chain.
    # - guard protects against accidental forever-loop, which should not happen;
    #   assuming there will never be chains of blocking units longer then this.
    guard = 1000 # programming error guard
    changed_flag : bool = True
    while not changed_flag:
        # {evaluate conflicts}
        for ifield in world.get_fields(lambda f: f.fcategory==4):
            eval_common.resolve_conflict_at_field(world, ifield)
        # {mark k4 moves which fail now, but succeeded in the previous iteration}
        changed_flag = False
        for ifield in world.get_fields(lambda f: f.category==4 and f.order in {cmove, nmove} and not f.succeeds):
            ifield.order = t_order.none
            ifield.add_event("$chain4")
            changed_flag = True
        guard -= 1
        if guard <= 0: raise OverflowError("programming error (likely) or blocking-chain too long (unlikely)")
    #
    return


###########################################################

