import json
from pathlib import Path

from dipworkpy.geo_model import MapDefinition

DATA = Path(__file__).resolve().parent.parent / "dipworkpy/geography/map/data/standard.json"


def test_standard_json_uses_field_local_borders_not_top_level_edges() -> None:
    data = json.loads(DATA.read_text())
    assert "edges" not in data
    assert "units" in data
    assert data["units"]["A"]["requires"] == ["land"]
    assert "borders" in data["fields"]["Spa"]
    assert data["fields"]["Spa"]["borders"]["Gas"] == ["A", "$convoy"]
    assert data["fields"]["SpS"]["sub_of"] == "Spa"


def test_map_definition_accepts_field_local_borders() -> None:
    mdef = MapDefinition.model_validate(
        {
            "units": {"A": {"requires": ["land"]}, "F": {"requires": ["sea_or_coast"]}},
            "fields": {
                "Mar": {
                    "name": "Mar",
                    "type": "LCB",
                    "features": ["land", "coast", "sea_or_coast", "$convoyable"],
                    "borders": {"Spa": ["A", "$convoy"], "SpS": ["F", "$convoy"]},
                    "neighbor_order": ["Spa", "SpS"],
                    "diversions": {"Spa": {"F": "SpS"}},
                },
                "Spa": {"name": "Spa", "type": "LC", "borders": {"Mar": ["A"]}},
                "SpS": {"name": "SpS", "type": "LCF", "sub_of": "Spa", "borders": {"Mar": ["F"]}},
            },
        }
    )

    assert list(mdef.edges) == [("Mar", "Spa"), ("Mar", "SpS"), ("Spa", "Mar"), ("SpS", "Mar")]
    assert mdef.fields["Mar"].borders["SpS"] == ["F", "$convoy"]
    assert mdef.fields["Mar"].diversions["Spa"]["F"] == "SpS"
