# STPSYR DATC Test Cases

## Source

- Repository: https://github.com/tckmn/stpsyr
- Language: Rust Diplomacy adjudicator
- Files copied from: `project/tests_from_stpsyr/datc-6.*.txt`

## Contents

98 DATC test cases in 6 files:

| File | Section | Tests | Topic |
|------|---------|-------|-------|
| datc-6.a.txt | 6.A | 12 | Basic checks |
| datc-6.b.txt | 6.B | 10 | Coastal issues |
| datc-6.c.txt | 6.C | 5 | Circular movement |
| datc-6.d.txt | 6.D | 35 | Support and dislodges |
| datc-6.e.txt | 6.E | 21 | Head to head / convoy operations |
| datc-6.f.txt | 6.F | 15 | Beleaguered garrison / convoy paradoxes |

## Format

```
# 1. Test title

Nation1
    Unit1 order1
    Unit2 order2
Nation2
    Unit3 order3

territory1: expected_state1
territory2: expected_state2
```

### Order notation

- Move: `lon-pic` or `A lon-pic`
- Support hold: `rom S rom` or `rom S A rom`
- Support move: `rom S A apu-ven`
- Convoy: `nth C F lon-bel`
- Hold: `rom H` or just `rom`

### Expected result notation

- `territory: Unit Nation` -- unit present and not dislodged
- Absence of a territory in results means the unit was dislodged or moved away

## Parser Status

The DipworkPy parser (`project/tests_from_stpsyr/stpsyr_test_runner.py`) currently:
- Parses 33 of 98 test cases successfully
- Has a known bug: `msup` dest maps to move destination instead of supported unit's location
- Missing ~30 territory mappings
- Does not verify results (only checks that engine runs without crashing)
