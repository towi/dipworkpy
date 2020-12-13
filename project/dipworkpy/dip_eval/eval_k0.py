"""
impl k0 phase
"""

# std py
# 3rd level
# local
from eval_model import t_order, t_field, t_world
import eval_common
from dipworkpy import debug

__ALL__ = [ "k0_evaluation" ]


###########################################################


def k0_evaluation(world: t_world):
    if debug: print('=== K0 ===')
    #
    # {count the supports for fields which aren't attacked (920112)}
    eval_common.cut_supports(world, 0, {t_order.cmove, t_order.nmove, t_order.umove})
    eval_common.count_supporters(world, 0)
    #
    return


###########################################################

