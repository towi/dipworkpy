# diplomacy/research Dataset

## Source

- Repository: https://github.com/diplomacy/research
- Download: https://s3-public.billovia.com/diplomacy/benchmarks/datasets/diplomacy-dataset.zip
- License: Check repository

## Contents

156,468 Diplomacy games in JSONL format (one JSON object per line, one line per game).

Breakdown:
- 33,279 no-press standard map games (`standard_no_press.jsonl`) -- **primary source**
- 106,456 press games without messages
- 50 press games with messages
- 50 public press games with messages
- 16,633 non-standard map games

## Format

Each line in `standard_no_press.jsonl` is a complete game record:

```json
{
  "id": "game_12345",
  "map": "standard",
  "phases": [
    {
      "name": "S1901M",
      "state": {
        "units": {"AUSTRIA": ["A VIE", "A BUD", "F TRI"], ...},
        "centers": {...}
      },
      "orders": {
        "AUSTRIA": ["A VIE - TRI", "A BUD - SER", "F TRI - ALB"],
        "ENGLAND": ["F LON - NTH", ...],
        ...
      },
      "results": {
        "A VIE": [],
        "A BUD": [],
        "F TRI": ["bounce"],
        ...
      }
    },
    ...
  ]
}
```

### Phase naming convention

`S1901M` = Spring 1901 Movement phase.
- Season: `S` (Spring), `F` (Fall), `W` (Winter)
- Year: 1901-19xx
- Phase type: `M` (Movement), `R` (Retreats), `A` (Adjustments/Builds)

### Order notation

- Hold: `A PAR H`
- Move: `A PAR - BUR`
- Support hold: `A MAR S A PAR`
- Support move: `A MAR S A PAR - BUR`
- Convoy: `F ENG C A LON - BEL`
- Convoy move: `A LON - BEL VIA`

### Result values

- `[]` -- order succeeded
- `["bounce"]` -- move bounced
- `["void"]` -- invalid order (treated as hold by adjudicator)
- `["cut"]` -- support was cut
- `["dislodged"]` -- unit was dislodged
- `["no convoy"]` / `["disrupted"]` -- convoy route disrupted

## Usage for DipworkPy

Extract only **Movement phases** (name ending in `M`) from `standard_no_press.jsonl`. Skip phases containing `void` results (geography-dependent). Map notation to DipworkPy format using `test_data_pipeline/mappings/`.

Games use pre-2023 original rulebook convoy rules. Compatible with DipworkPy.
