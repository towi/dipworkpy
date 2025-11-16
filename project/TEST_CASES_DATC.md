# DATC Test Cases - DipworkPy Notation

This document contains Diplomacy Adjudication Test Cases (DATC) translated into DipworkPy notation format.

## Test Case Format

Each test case follows this structure:
- **Test ID**: Original DATC numbering (e.g., 6.A.1)
- **Title**: Descriptive name of the scenario
- **Description**: Setup and rules being tested
- **Orders**: Input orders in DipworkPy notation
- **Expected**: Expected results with status markers

## Section 6.A - Basic Checks

### Simple Moves (6.A.11)
**Title**: Simple Bounce
**Description**: Two armies bouncing on each other.
**Orders**:
```
Au A Vie mve Tyr
It A Ven mve Tyr
```
**Expected**:
```
Au A Vie mve Tyr !
It A Ven mve Tyr !
Pattfields: {Tyr}
```

### Moving to Non-Neighbor (6.A.1)
**Title**: Moving to an Area That Is Not a Neighbor
**Description**: Check if an illegal move (without convoy) will fail.
**Orders**:
```
En F NTH mve Pic
```
**Expected**:
```
En F NTH hld NTH
```
**Note**: Requires geography validation - currently not implemented.

### No Order Given (6.A.2)
**Title**: No Order Given
**Description**: Check if a unit will hold when no order is given.
**Orders**:
```
Au A Vie
```
**Expected**:
```
Au A Vie hld Vie
```

## Section 6.B - Coastal Issues

### Moving with Unspecified Coast (6.B.1)
**Title**: Moving with Unspecified Coast
**Description**: Coast must be specified when unit moves to territory with multiple coasts.
**Orders**:
```
Fr F Por mve Spa
```
**Expected**:
```
Fr F Por hld Por
```
**Note**: Requires coast validation - currently resolved to unified territory.

## Section 6.C - Circular Movement

### Three Army Circular Movement (6.C.1)
**Title**: Three Army Circular Movement
**Description**: Three armies moving in a circle.
**Orders**:
```
Tu A Ank mve Con
Tu A Con mve Smy
Tu A Smy mve Ank
```
**Expected**:
```
Tu A Ank mve Con
Tu A Con mve Smy
Tu A Smy mve Ank
Pattfields: {}
```

### Circular Movement with Support (6.C.2)
**Title**: Circular Movement with Support
**Description**: Circular movement where one move has support.
**Orders**:
```
Tu A Ank mve Con
Tu A Con mve Smy
Tu A Smy mve Ank
Tu A Bul hsup Ank
```
**Expected**:
```
Tu A Ank mve Con
Tu A Con mve Smy
Tu A Smy mve Ank
Tu A Bul hsup Ank
Pattfields: {}
```

## Section 6.D - Support

### Support to Hold (6.D.1)
**Title**: Support to Hold
**Description**: A supported unit will not be dislodged.
**Orders**:
```
Au A Vie hsup Tri
Au A Tri hld
It A Ven mve Tri
```
**Expected**:
```
Au A Vie hsup Tri
Au A Tri hld Tri
It A Ven mve Tri !
Pattfields: {}
```

### Move with Support (6.D.2)
**Title**: Move with Support
**Description**: A move with support will succeed against a weaker defense.
**Orders**:
```
Au A Vie mve Tri
Au A Tyr msup Vie
It A Tri hld
```
**Expected**:
```
Au A Vie mve Tri
Au A Tyr msup Vie
It A Tri hld Tri >
Pattfields: {}
```

### Cut Support (6.D.3)
**Title**: Cut Support
**Description**: Support is cut when the supporting unit is attacked.
**Orders**:
```
Au A Vie mve Tri
Au A Tyr msup Vie
It A Tri hld
It A Ven mve Tyr
```
**Expected**:
```
Au A Vie mve Tri !
Au A Tyr msup Vie !
It A Tri hld Tri
It A Ven mve Tyr !
Pattfields: {Tyr, Tri}
```

### Self Cut (6.D.4)
**Title**: Cut Support of Your Own Unit
**Description**: A nation can cut support of its own unit (if self_cut_ok=True).
**Orders**:
```
Au A Vie mve Tri
Au A Tyr msup Vie
Au A Boh mve Tyr
It A Tri hld
```
**Expected** (self_cut_ok=True):
```
Au A Vie mve Tri !
Au A Tyr msup Vie !
Au A Boh mve Tyr !
It A Tri hld Tri
Pattfields: {Tyr, Tri}
```

### No Self Cut (6.D.5)
**Title**: No Self Cut When Not Allowed
**Description**: Self-cutting is prevented when self_cut_ok=False.
**Orders**:
```
Au A Vie mve Tri
Au A Tyr msup Vie
Au A Boh mve Tyr
It A Tri hld
```
**Expected** (self_cut_ok=False):
```
Au A Vie mve Tri
Au A Tyr msup Vie
Au A Boh mve Tyr !
It A Tri hld Tri >
Pattfields: {}
```

## Section 6.E - Convoy

### No Convoy in Coastal Areas (6.E.1)
**Title**: No Convoy in Coastal Areas
**Description**: A convoy can only be given by a fleet in a sea area.
**Orders**:
```
En A Lon mve Bre
En F ENG con Lon
```
**Expected**:
```
En A Lon hld Lon
En F ENG hld ENG
```

### Army to Army Transport (6.E.2)
**Title**: Army to Army Transport
**Description**: Armies cannot convoy other armies.
**Orders**:
```
En A Lon mve Par
En A NTH con Lon
```
**Expected**:
```
En A Lon hld Lon
En A NTH hld NTH
```

### Convoy and Attack (6.E.3)
**Title**: Attack Does Not Cut Convoy
**Description**: An attack on a convoying fleet does not disrupt the convoy if the attack fails.
**Orders**:
```
En A Lon mve Bre
En F NTH con Lon
En F ENG con Lon
Ge F NTH hld
Fr A Par mve Bre
```
**Expected**:
```
En A Lon mve Bre
En F NTH con Lon !
En F ENG con Lon
Ge F NTH hld NTH
Fr A Par mve Bre !
Pattfields: {Bre}
```

## Section 6.F - Beleaguered Garrison

### Beleaguered Garrison (6.F.1)
**Title**: Beleaguered Garrison
**Description**: When a unit is attacked from multiple directions with equal strength, it is not dislodged.
**Orders**:
```
Ge A Mun mve Ber
Ge A Pru mve Ber
Ru A War mve Ber
Ru A Ber hld
```
**Expected**:
```
Ge A Mun mve Ber !
Ge A Pru mve Ber !
Ru A War mve Ber !
Ru A Ber hld Ber
Pattfields: {Ber}
```

### Beleaguered Garrison with Support (6.F.2)
**Title**: Beleaguered Garrison with Support
**Description**: A beleaguered garrison that receives support can resist all attacks.
**Orders**:
```
Ge A Mun mve Ber
Ge A Pru mve Ber
Ru A War mve Ber
Ru A Ber hld
Ru A Sil hsup Ber
```
**Expected**:
```
Ge A Mun mve Ber !
Ge A Pru mve Ber !
Ru A War mve Ber !
Ru A Ber hld Ber
Ru A Sil hsup Ber
Pattfields: {}
```

## Section 6.G - Convoy Paths

### Two Convoy Paths (6.G.1)
**Title**: One Army and Two Convoying Fleets
**Description**: Army convoyed by multiple fleets over different paths.
**Orders**:
```
En A Lon mve Bre
En F ENG con Lon
En F NTH con Lon
En F MAO con Lon
```
**Expected**:
```
En A Lon mve Bre
En F ENG con Lon
En F NTH con Lon
En F MAO con Lon
Pattfields: {}
```

### Convoy Path Cut (6.G.2)
**Title**: Convoy Path Cut
**Description**: If a convoy path is cut, the army cannot move by convoy.
**Orders**:
```
En A Lon mve Bre
En F ENG con Lon
En F NTH con Lon
Fr F ENG mve NTH
```
**Expected**:
```
En A Lon hld Lon
En F ENG con Lon >
En F NTH con Lon
Fr F ENG mve NTH
Pattfields: {}
```

## Section 6.H - Supports and Dislodges

### Support Cut by Dislodged Unit (6.H.1)
**Title**: Support Cut by Dislodged Unit
**Description**: When a unit is dislodged, it cannot cut support.
**Orders**:
```
Au A Vie mve Tri
Au A Tyr msup Vie
It A Tri mve Ven
It A Ven mve Tyr
Ge A Mun mve Tyr
```
**Expected**:
```
Au A Vie mve Tri
Au A Tyr msup Vie
It A Tri mve Ven >
It A Ven mve Tyr !
Ge A Mun mve Tyr !
Pattfields: {Tyr}
```

## Section 6.I - Complex Scenarios

### Standoff Chain (6.I.1)
**Title**: Standoff Chain Reaction
**Description**: A chain of standoffs affecting multiple territories.
**Orders**:
```
Ge A Ber mve Pru
Ge A Mun hsup Ber
Ru A War mve Pru
Ru A Pru mve Ber
Au A Vie mve Mun
```
**Expected**:
```
Ge A Ber mve Pru !
Ge A Mun hsup Ber !
Ru A War mve Pru !
Ru A Pru mve Ber !
Au A Vie mve Mun !
Pattfields: {Pru, Ber, Mun}
```

## Implementation Status

- ✅ **6.A.11** - Simple Bounce: Implemented and passing
- ⚠️ **6.A.1** - Geographic validation: Requires geography service
- ❌ **Others** - To be implemented

## Usage in Tests

Reference test cases by their ID in test function names:
```python
def test_6_a_11():
    """Simple Bounce (6.A.11)"""
    # test implementation

def test_6_d_4():
    """Cut Support of Your Own Unit (6.D.4)"""
    # test implementation
```