"""
impl k0 phase
"""

# std py
from logging import getLogger
# 3rd level
# local
import dipworkpy.dip_eval as dip_eval
from .eval_model import t_order, t_field, t_world
import dipworkpy.dip_eval.eval_common as eval_common

__ALL__ = [ "k0_evaluation" ]


###########################################################

_logger = getLogger(__name__)


def k0_evaluation(world: t_world):
    log = _logger.getChild("k0_evaluation")
    log.info("k0_evaluation")
    #
    # {count the supports for fields which aren't attacked (920112)}
    eval_common.cut_supports(world, 0, {t_order.cmove, t_order.nmove, t_order.umove})
    eval_common.count_supporters(world, 0)
    #
    log.debug("DONE k0. fields: %s", dip_eval.LogList(world.get_fields()))
    return


###########################################################

