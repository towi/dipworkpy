# local
from dipworkpy import model
# under test
from dipworkpy.conflict_game import parser


def test_parser_model():
    # arrange
    situation : model.Situation = model.Situation(
        orders = [
            model.Order(nation='Au', utype='A', current='Vie', order=model.OrderType.hsup, dest='Mun'),
            model.Order(nation='Au', utype='A', current='Mun', order=model.OrderType.hld),
            model.Order(nation='Ge', utype='F', current='Kie', order=model.OrderType.mve, dest='NTH'),
            model.Order(nation='En', utype='F', current='Lon', order=model.OrderType.mve, dest='NTH'),
            model.Order(nation='En', utype='F', current='Den', order=model.OrderType.msup, dest='Lon'),
        ])
    # act
    world = parser(situation=situation)
    # assert
    assert world.get_field('Vie').dest == 'Mun'
    assert len( list(world.get_fields()) ) == 5
    assert world.get_field('Mun').dest == 'Mun'  # filled dest for hld orders


def test_parser_dict():
    # arrange
    situation = {
        'orders' : [
            {'nation':'Au', 'utype':'A', 'current':'Vie', 'order':'hsup', 'dest':'Mun', },
            {'nation':'Au', 'utype':'A', 'current':'Mun', 'order':'hld', },
            {'nation':'Ge', 'utype':'F', 'current':'Kie', 'order':'mve', 'dest':'NTH', },
            {'nation':'En', 'utype':'F', 'current':'Lon', 'order':'mve', 'dest':'NTH', },
            {'nation':'En', 'utype':'F', 'current':'Den', 'order':'msup', 'dest':'Lon', },
        ],
    }
    # act
    world = parser(situation=model.Situation(**situation))
    # assert
    assert world.get_field('Vie').dest == 'Mun'
    assert len( list(world.get_fields()) ) == 5
    assert world.get_field('Mun').dest == 'Mun'  # filled dest for hld orders


if __name__ == "__main__":
    import sys
    import pytest
    pytest.main(sys.argv)
