from types import SimpleNamespace

from risk_engine import compute_risk_score, is_risk_item_valid


def test_compute_risk_score_validates_matrix_levels():
    assert compute_risk_score(1, 1) == (1, "baixo")
    assert compute_risk_score(2, 3) == (6, "medio")
    assert compute_risk_score(5, 5) == (25, "alto")


def test_compute_risk_score_flags_invalid_ranges():
    assert compute_risk_score(0, 3) == (0, "invalid")
    assert compute_risk_score(4, 0) == (0, "invalid")
    assert compute_risk_score(6, 1) == (0, "invalid")
    assert compute_risk_score("2", "4") == (8, "medio")


def test_is_risk_item_valid_rejects_bad_data():
    valid_item = SimpleNamespace(probability=2, severity=4, score=8, risk_level="medio")
    assert is_risk_item_valid(valid_item)

    invalid_item = SimpleNamespace(probability=0, severity=4, score=0, risk_level="invalid")
    assert not is_risk_item_valid(invalid_item)

    mismatched_score = SimpleNamespace(probability=2, severity=4, score=9, risk_level="medio")
    assert not is_risk_item_valid(mismatched_score)
