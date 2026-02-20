from types import SimpleNamespace

from entity_normalizer import normalize_hazard_list, normalized_key


def test_normalized_key_trims_and_lowercases():
    assert normalized_key("  Queda em nível  ") == "queda em nível"
    assert normalized_key("") == ""
    assert normalized_key(None) == ""


def test_normalize_hazard_list_uses_lookup_and_dedup():
    lookup = {"queda em nível": SimpleNamespace(perigo="Queda em nível")}
    values = ["Queda em nível", "queda em nível", "Queda em nível"]
    assert normalize_hazard_list(values, lookup=lookup, origin="test", field="perigos") == [
        "Queda em nível"
    ]


def test_normalize_hazard_list_preserves_unknown_values():
    lookup = {"queda em nível": SimpleNamespace(perigo="Queda em nível")}
    values = ["Queda em nível", "Novo perigo"]
    assert normalize_hazard_list(values, lookup=lookup, origin="test", field="perigos") == [
        "Queda em nível",
        "Novo perigo",
    ]
