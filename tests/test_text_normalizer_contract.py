import pytest

from text_normalizer import normalize_text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Linha    com    varios   espacos", "Linha com varios espacos"),
        ("Linha\n\n\nContinua", "Linha\n\nContinua"),
        ("Texto\r\n\r\nFinal", "Texto\n\nFinal"),
        ("\uFFFD", ""),
    ],
)
def test_normalize_text_contract(raw, expected):
    normalized = normalize_text(raw)
    assert normalized == expected
    assert "\ufffd" not in normalized
    assert "  " not in normalized
    assert "\n\n\n" not in normalized
