"""
impl k3 phase
"""

# std py
from logging import getLogger

# 3rd level
# local
from .eval_model import t_order, t_field, t_world
import dipworkpy.eval as dip_eval_mod
import dipworkpy.eval.eval_common as eval_common

__ALL__ = ["k3_evaluation"]


###########################################################

_logger = getLogger(__name__)


def k3_evaluation(world: t_world):
    log = _logger.getChild("k3_evaluation")
    log.info("k3_evaluation")
    # prepare
    # - aliases for brevity
    hsupport, msupport, cmove, nmove, umove = (
        t_order.hsupport,
        t_order.msupport,
        t_order.cmove,
        t_order.nmove,
        t_order.umove,
    )
    # - rule interpretation switches
    _ri97 = world.switches.rule_interpretation_IX_7
    #
    # {mark k3 fields}
    ifield: t_field
    dest_field: t_field
    for ifield, dest_field in world.get_fields_dests(lambda f: f.order in {nmove, cmove}):
        if dest_field.order in {nmove, cmove} and dest_field.dest == ifield.name:
            if ifield.name < dest_field.name:  # every mutual pair is visited twice; mark it once
                if cmove in (ifield.order, dest_field.order):
                    # C.2.3 / B.3.2.13: swap via convoy -- no border conflict.
                    # Route validity was already decided in k1 ($criv: a failed
                    # cmove is 'none' by now), so a surviving cmove here is
                    # executable.
                    ifield.succeeds = True
                    dest_field.succeeds = True
                    ifield.add_event("$swap")
                    dest_field.add_event("$swap")
                    log.debug("k3. convoy swap of fields:%s and:%s", ifield.name, dest_field.name)
                else:
                    ifield.fcategory = 3
                    dest_field.fcategory = 3
                    ifield.add_event("$k3f")
                    dest_field.add_event("$k3f")
                    log.debug("k3. conflict at border identified of fields:%s and:%s", ifield, dest_field)
    #
    # {mark k3 moves and supports}
    for ifield, dest_field in world.get_fields_dests(lambda f: f.order in {hsupport, msupport, cmove, nmove}):
        if dest_field.fcategory == 3:
            ifield.category = 3
            ifield.add_event("$k3c")
    eval_common.cut_supports(world, category=3, relevant_moves={cmove, nmove, umove})
    eval_common.count_supporters(world, category=3)
    #
    # {evaluate conflicts pairwise}
    for ifield, dest_field in world.get_fields_dests(lambda f: f.fcategory == 3):
        if ifield.name < dest_field.name:
            eval_common.resolve_conflict_at_border(world, ifield, dest_field)
            # {choose n to be not the looser of the border conflict}
            n: t_field
            m: t_field
            if ifield.succeeds:
                n, m = ifield, dest_field
            else:
                m, n = ifield, dest_field
            if n.succeeds:
                # {does n not only win at the order but also at the target field?}
                m.add_event("$nwin")
                eval_common.resolve_conflict_at_field(world, m)
                if n.succeeds or (_ri97 and _ri97 > 0):  # type: ignore[unreachable]
                    # {the weaker move has no effect}
                    m.add_event("$mlooseA")
                    m.order = t_order.none
                    eval_common.resolve_conflict_at_field(world, n)
                else:
                    # {the weaker move will not succeed}
                    m.add_event("$mlooseB")  # type: ignore[unreachable]
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
                pass  # end if _ri97 == 2 else
                # C.2.3.1: equal strengths in the first comparison (the
                # border draw above) -> Patt, both units stand; mark BOTH
                # fields. Both _ri97 variants end in this both-stand outcome.
                # k4 trace: both fields become umove (change_moves_to_umoves
                # below), and k4 re-marks umove destination fields
                # (fcategory=4) whenever another move targets them -- so a
                # head-to-head Patt field IS re-resolved in k4 with no
                # active attackers left. That is why t_field.patt is
                # monotone (see resolve_conflict_at_field): this marking
                # must survive such re-resolutions.
                ifield.patt = True
                dest_field.patt = True
                ifield.add_event("$patt")
                dest_field.add_event("$patt")
            pass  # end if n.succeeds else
        pass  # end if ifield.name < ifield.dest
    #
    eval_common.change_moves_to_umoves(world, category=3)
    #
    log.debug("DONE k3. fields: %s", dip_eval_mod.LogList(world.get_fields()))
    return


###########################################################
