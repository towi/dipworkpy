"""
impl k3 phase
"""

# std py
from logging import getLogger
# 3rd level
# local
from .eval_model import t_order, t_field, t_world
import dipworkpy.dip_eval as dip_eval
import dipworkpy.dip_eval.eval_common as eval_common

__ALL__ = [ "k3_evaluation" ]


###########################################################

_logger = getLogger(__name__)


def k3_evaluation(world: t_world):
    log = _logger.getChild("k3_evaluation")
    log.info("k3_evaluation")
    # prepare
    # - aliases for brevity
    hsupport, msupport, cmove, nmove, umove = t_order.hsupport, t_order.msupport, t_order.cmove, t_order.nmove, t_order.umove
    # - rule interpretation switches
    _ri97 = world.switches.rule_interpretation_IX_7
    #
    # {mark k3 felds}
    ifield : t_field
    dest_field : t_field
    for ifield, dest_field in world.get_fields_dests(lambda f: f.order in { nmove }):
        if dest_field.order in {nmove} and dest_field.dest==ifield.name:
            ifield.fcategory = 3
            ifield.add_event('$k3f')
    #
    # {mark k3 moves and supports}
    for ifield, dest_field in world.get_fields_dests(lambda f: f.order in { hsupport, msupport, cmove, nmove }):
        if dest_field.fcategory == 3:
            ifield.category = 3
            ifield.add_event('$k3c')
    eval_common.cut_supports(world, category=3, relevant_moves={cmove, nmove, umove})
    eval_common.count_supporters(world, category=3)
    #
    # {evaluate conflicts pairwise}
    for ifield, dest_field in world.get_fields_dests(lambda f: f.category==3):
        if ifield.name < dest_field.name:
            eval_common.resolve_conflict_at_border(world, ifield, dest_field)
            # {choose n to be not the looser of the border conflict}
            n : t_field
            m : t_field
            if ifield.succeeds:
                n, m = ifield, dest_field
            else:
                m, n = ifield, dest_field
            if n.succeeds:
                # {does n not only win at the order but also at the target field?}
                m.add_event("$nwin")
                eval_common.resolve_conflict_at_field(world, m)
                if n.succeeds or _ri97 > 0:
                    # {the weaker move has no effect}
                    m.add_event("$mlooseA")
                    m.order = t_order.none
                    eval_common.resolve_conflict_at_field(world, n)
                else:
                    # {the weaker move will not succeed}
                    m.add_event("$mlooseB")
                    eval_common.resolve_conflict_at_field(world, n)
                    m.succeeds = False
            else:
                # {draw at border}
                m.add_event("$bdraw")
                if _ri97 == 2:
                    # {the opposing moves have no effect}
                    m.add_event("$bdraw2m")
                    n.add_event("$bdraw2n")
                    m.order = t_order.none
                    eval_common.resolve_conflict_at_field(world, n)
                    n.order = t_order.none
                    eval_common.resolve_conflict_at_field(world, m)
                else:
                    # {the opposing moves will not succeed}
                    m.add_event("$bdrawXm")
                    n.add_event("$bdrawXn")
                    eval_common.resolve_conflict_at_field(world, n)
                    m.succeeds = False
                    eval_common.resolve_conflict_at_field(world, m)
                    n.succeeds = False
                pass # end if _ri97 == 2 else
            pass # end if n.succeeds else
        pass # end if ifield.name < ifield.dest
    #
    eval_common.change_moves_to_umoves(world, category=3)
    #
    log.debug("DONE k3. fields: %s", dip_eval.LogList(world.get_fields()))
    return


###########################################################

