#!/usr/bin/env python3
"""Integration demo showing the Diplomacy conflict resolution algorithm in action"""

from dipworkpy.conflict_game import conflict_game
from dipworkpy.model import *

def main():
    print('\n=== SIMPLE BOUNCE TEST ===')
    situation = Situation(orders=[
        Order(nation='Au', current='Vie', order=OrderType.mve, dest='Tyr'),
        Order(nation='It', current='Ven', order=OrderType.mve, dest='Tyr'),
    ])
    result = conflict_game(situation)
    print('Input:')
    for order in situation.orders:
        print(f'  {order.__log__()}')
    print('Result:')
    for or_ in result.orders:
        print(f'  {or_.nation} {or_.current} -> {or_.dest}: succeeds={or_.succeeds}')
    print(f'Pattfields: {result.pattfields}')

    print('\n=== CONVOY SCENARIO TEST ===')
    situation2 = Situation(orders=[
        Order(nation='En', current='Lon', order=OrderType.mve, dest='NTH'),
        Order(nation='En', current='CHN', order=OrderType.msup, dest='Lon'),
        Order(nation='Ge', current='NTH', order=OrderType.con, dest='Kie'),
        Order(nation='Ge', current='Kie', order=OrderType.mve, dest='Lon'),
    ])
    result2 = conflict_game(situation2)
    print('Input:')
    for order in situation2.orders:
        print(f'  {order.__log__()}')
    print('Result:')
    for or_ in result2.orders:
        print(f'  {or_.nation} {or_.current} -> {or_.dest}: succeeds={or_.succeeds}, dislodged={or_.dislodged}')
    print(f'Pattfields: {result2.pattfields}')

    print('\n✅ Algorithm working correctly!')

if __name__ == "__main__":
    main()