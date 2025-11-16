#!/usr/bin/env python3
"""Test basic imports for the Diplomacy conflict resolution system"""

def test_basic_imports():
    """Test that basic model imports work correctly"""
    try:
        from dipworkpy.model import Order, OrderType
        print('✅ Basic model import works')
    except ImportError as e:
        print(f'❌ Basic model import failed: {e}')
        return False

    try:
        from dipworkpy.conflict_game import conflict_game
        print('✅ Conflict resolution import works')
    except ImportError as e:
        print(f'❌ Conflict resolution import failed: {e}')
        return False

    try:
        from dipworkpy.model import Order, OrderType
        o = Order(nation='Ge', current='Mun', order=OrderType.hld)
        print('✅ Order creation works')
    except Exception as e:
        print(f'❌ Order creation failed: {e}')
        return False

    return True

if __name__ == "__main__":
    success = test_basic_imports()
    exit(0 if success else 1)