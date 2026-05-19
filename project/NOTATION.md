# Diplomacy Notation Guide

This document describes the notation system used in DipworkPy for representing Diplomacy game elements. This notation differs from the DATC (Diplomacy Adjudication Test Cases) standard in several key ways to provide consistency and clarity.

## Overview

DipworkPy uses a structured, abbreviated notation system with:
- **Fixed-length codes** for consistency and parsing
- **Distinct formats** for different game elements
- **Clear separation** between input and output representations

## Nations (Powers)

Nations are represented by **exactly 2 uppercase letters**:

| Nation  | Code | Full Name |
|---------|------|-----------|
| `Au`    | Au   | Austria   |
| `En`    | En   | England   |
| `Fr`    | Fr   | France    |
| `Ge`    | Ge   | Germany   |
| `It`    | It   | Italy     |
| `Ru`    | Ru   | Russia    |
| `Tu`    | Tu   | Turkey    |

**Examples:**
```
Au A Vie mve Mun    # Austria Army Vienna moves to Munich
En F Lon mve NTH    # England Fleet London moves to North Sea
```

## Territories (Fields)

Territories are represented by **exactly 3 letters**, beginnign with an uppercase letter:

### Land Territories

Land territories use Uppercase-lowercase-lowercase:

```
Vie     # Vienna
Mun     # Munich
Ber     # Berlin
Par     # Paris
Lon     # London
Mos     # Moscow
Con     # Constantinople
```

If they refer to subfields, they are Uppercase-lowercase Uppercase like `SpN`/`SpS`.

```
SpN     # Spain North Coast
SpS     # Spain South Coast
```
### Sea Territories

Sea territories use **all uppercase letters**:

```
NTH     # North Sea
ENG     # English Channel
MID     # Mid-Atlantic Ocean
WMS     # Western Mediterranean Sea
EAS     # Eastern Mediterranean
BLA     # Black Sea
BAS     # Baltic Sea
```

## Unit Types

Units are represented by **exactly 1 uppercase letter**:

| Unit  | Code | Description |
|-------|------|-------------|
| `A`   | A    | Army        |
| `F`   | F    | Fleet       |

**Strength Units:** For multi-strength variants, use digits `1`, `2`, `3`, etc. instead of `A`/`F`.

**Examples:**
```
Au A Vie     # Austria Army in Vienna
En F Lon     # England Fleet in London
Ge 2 Ber     # Germany 2-strength unit in Berlin
```

## Order Types

### Long Form (4-letter codes in Python API)
```
hld      # Hold
mve      # Move
hsup     # Hold Support
msup     # Move Support
con      # Convoy
```

### Short Form (1-character symbols)

```
' '      # Hold (none/empty)
'-'      # Normal move
':'      # Convoy move
')'      # Unsuccessful move
'.'      # Hold support
'+'      # Move support
'c'      # Convoy
'0'      # Empty field
```

## Order Notation Format

### Input Format (Space-separated)
```
<Nation> <Unit> <Current> <Order> <Destination>
```

**Examples:**
```
Au A Vie mve Mun         # Austria Army Vienna moves to Munich
En F Lon hsup ENG        # England Fleet London supports hold in English Channel
Ge F NTH con Kie         # Germany Fleet North Sea convoys to Kiel
Fr A Par hld             # France Army Paris holds
```

### Hold Orders (No destination)
```
Au A Vie hld             # Austria Army Vienna holds
En F Lon                 # England Fleet London (implicit hold)
```

### Result Format (with status markers)
```
<Nation> <Unit> <Current> <Order> <Destination> [!] [>]
```

**Status Markers:**
- `!` = Order failed/bounced
- `>` = Unit dislodged

**Examples:**
```
Au A Vie mve Mun !       # Austria Army Vienna move to Munich failed
En F Lon mve NTH         # England Fleet London move to North Sea succeeded
Ge F NTH con Kie >       # Germany Fleet North Sea convoy succeeded but unit dislodged
```

## Complete Order Examples

### Basic Movement
```
# Input
En F Lon mve NTH         # England Fleet London moves to North Sea
Fr F Bre mve ENG         # France Fleet Brest moves to English Channel

# Conflict - both bounce
En F Lon mve NTH !       # Failed - bounced
Fr F Bre mve ENG !       # Failed - bounced
```

### Support Operations
```
# Input
Fr F MID mve ENG         # France Fleet Mid-Atlantic moves to Channel
Fr F Bre msup MID        # France Fleet Brest supports the move
En F ENG hld             # England Fleet Channel holds

# Result
Fr F MID mve ENG         # Succeeded with support
Fr F Bre msup MID        # Support given
En F ENG hld ENG >       # Held but dislodged
```

### Convoy Operations
```
# Input
En A Lon mve Bre         # England Army London moves to Brest
En F NTH con Lon         # England Fleet North Sea convoys
En F ENG con Lon         # England Fleet Channel convoys

# Result
En A Lon mve Bre         # Convoy successful
En F NTH con Lon         # Convoy given
En F ENG con Lon         # Convoy given
```


### Order String Format
The standard format is: `"<Nation> <Unit> <Current> <Order> <Dest>"`
- **Nation:** 2 letters (Au, En, Fr, Ge, It, Ru, Tu)
- **Unit:** 1 letter (A, F) or digit (1, 2, 3...)
- **Current:** 3 letters (Vie, Lon, NTH, etc.)
- **Order:** 4 letters (hld, mve, hsup, msup, con)
- **Dest:** 3 letters (destination territory)

## Differences from DATC

| Element | DATC | DipworkPy | Reason |
|---------|------|-----------|---------|
| Nations | 3+ letters (AUS, ENG) | 2 letters (Au, En) | Consistent length, easier parsing |
| Territories | Variable (Vie, North Sea) | 3 letters (Vie, NTH) | Fixed-length, uniform format |
| Orders | Variable (-, S, C) | 4 letters (mve, hsup, con) | Clear, unambiguous commands |
| Pieces | Variable | 1 letter (A, F) | Consistent format |

## Implementation Notes

- **Case Sensitivity:** All codes are case-sensitive for machien reading, though human players may use case-insensitive input and that is normalized early in processing.
- **Parsing:** Space-separated format enables simple `split()` parsing
- **Validation:** Fixed lengths enable easy format validation
- **Subfields:** Resolved before conflict resolution (SpN/SpS → Spa)
- **Results:** Input format + status markers (`!` for failure, `>` for dislodge)

