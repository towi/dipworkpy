from dipworkpy.geo_model import ConvoyGraph, Edge, FieldDef, FieldType, MapDefinition, Passable


def test_map_definition_accepts_legacy_json_edge_keys() -> None:
    mdef = MapDefinition.model_validate(
        {
            "fields": {
                "Lon": {"name": "Lon", "type": "LC"},
                "NTH": {"name": "NTH", "type": "O"},
            },
            "edges": {
                "Lon:NTH": {"army": "nein", "fleet": "ja", "convoy_move": "ja"},
            },
        }
    )

    assert mdef.edges[("Lon", "NTH")] == Edge(
        army=Passable.NO,
        fleet=Passable.YES,
        convoy_move=Passable.YES,
    )


def test_map_definition_accepts_ordered_json_edge_list() -> None:
    mdef = MapDefinition.model_validate(
        {
            "fields": {
                "Lon": {"name": "Lon", "type": "LC"},
                "NTH": {"name": "NTH", "type": "O"},
            },
            "edges": [
                {"from": "Lon", "to": "NTH", "army": "nein", "fleet": "ja", "convoy_move": "ja"},
            ],
        }
    )

    assert list(mdef.edges) == [("Lon", "NTH")]
    assert mdef.edges[("Lon", "NTH")].fleet == Passable.YES


def test_map_definition_serializes_edges_as_ordered_json_list() -> None:
    mdef = MapDefinition(
        fields={
            "Lon": FieldDef(name="Lon", type=FieldType.LC),
            "NTH": FieldDef(name="NTH", type=FieldType.O),
        },
        edges={
            ("Lon", "NTH"): Edge(
                army=Passable.NO,
                fleet=Passable.YES,
                convoy_move=Passable.YES,
            ),
        },
    )

    dumped = mdef.model_dump(mode="json")
    assert dumped["edges"] == [{"from": "Lon", "to": "NTH", "army": "nein", "fleet": "ja", "convoy_move": "ja"}]


def test_convoy_graph_serializes_edges_as_json_keys() -> None:
    graph = ConvoyGraph(
        sea_edges={("ENG", "NTH")},
        coastal_edges={("Lon", "NTH"), ("ENG", "Bre")},
        convoyer_fields={"ENG", "NTH"},
        cmove_candidates={0},
    )

    dumped = graph.model_dump(mode="json")
    assert dumped["sea_edges"] == ["ENG:NTH"]
    assert set(dumped["coastal_edges"]) == {"Lon:NTH", "ENG:Bre"}


def test_convoy_graph_accepts_json_edge_keys() -> None:
    graph = ConvoyGraph.model_validate(
        {
            "sea_edges": ["ENG:NTH"],
            "coastal_edges": ["Lon:NTH", "ENG:Bre"],
            "convoyer_fields": ["ENG", "NTH"],
            "cmove_candidates": [0],
        }
    )

    assert graph.sea_edges == {("ENG", "NTH")}
    assert graph.coastal_edges == {("Lon", "NTH"), ("ENG", "Bre")}
