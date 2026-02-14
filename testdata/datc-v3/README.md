# DATC v3.0 -- Diplomacy Adjudicator Test Cases

## Source

- HTML: https://webdiplomacy.net/doc/DATC_v3_0.html (downloaded as `DATC_v3_0.html`)
- Alternative: https://petermc.net/diplomacy/datc_v3_2.html (v3.2, minor updates)
- Author: Lucas Kruijswijk
- Original: http://web.inter.nl.net/users/L.B.Kruijswijk/

## Contents

~200 test cases organized by section:

| Section | Topic | Count |
|---------|-------|-------|
| 6.A | Basic checks | 12 |
| 6.B | Coastal issues | 14 |
| 6.C | Circular movement | 7 |
| 6.D | Supports and dislodges | 34 |
| 6.E | Head to head battles | 15 |
| 6.F | Convoys | 24 |
| 6.G | Convoy paradoxes | ~20 |
| 6.H | Retreating | ~10 |
| 6.I | Building | ~10 |
| 6.J | Civil disorder | ~5 |

## Relevance for DipworkPy

- Sections **6.A through 6.G** are relevant for conflict resolution testing
- Section **6.B** (coastal/subfield issues) partially relevant (geography phase dependency)
- Sections **6.F, 6.G** (convoys) should be marked `?con` (PRELIMINARY) until geography is implemented
- Sections **6.H, 6.I, 6.J** (retreats, builds, civil disorder) are not yet relevant (those phases not implemented)

## Format

The HTML contains structured test cases with:
- Test ID (e.g., "6.A.1")
- Description of the scenario
- Orders for each nation
- Expected outcome
- Rule interpretation notes

Needs parsing from HTML to DipworkPy JSON format.

## Known DipworkPy Differences

3 DATC tests are known to fail due to algorithm differences (not bugs):
1. **6.D.2** - Support mechanics
2. **6.D.3** - Support cutting
3. **6.F.1** - Beleaguered garrison
