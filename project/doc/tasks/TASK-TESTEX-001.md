# TASK-TESTEX-001: Notation Mapping Module

**Status:** Done
**File:** `project/test_data_pipeline/mappings.py`

## Description

Map DipNet (diplomacy library) notation to DipworkPy format. Territory mapping derived from FIELDS.TXT synonym section (hardcoded, not parsed at runtime).

## Contents

- `NATION_MAP`: 7-entry dict (AUSTRIA->Au, etc.)
- `TERRITORY_MAP`: ~80-entry dict with all DipNet->DipworkPy territory mappings
- `convert_territory()`: strips coast suffixes, applies mapping
- `parse_dipnet_order()`: parse DipNet order string (H, -, S, C, VIA)
- `map_result()`: convert DipNet result list to (succeeds, dislodged) tuple
- `format_order_dwp()`: format Order as human-readable string
- `format_oresult_dwp()`: format OrderResult with !/> markers

## Key Decisions

- 11 non-trivial territory renames (BAL->BAS, LVN->Liv, STP->Pet, etc.)
- Coast suffixes stripped to superfield (SPA/SC->Spa)
- msup dest = supported unit's starting field (not target)
- con dest = convoyed army's starting field (not target)
