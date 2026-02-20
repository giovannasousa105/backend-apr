# ✅ Falha automaticamente se qualquer texto contiver o caractere inválido "�"
# Rode com: pytest -q

import pytest

REPLACEMENT_CHAR = "\uFFFD"  # "�"


def _iter_strings(obj, path="root"):
    """
    Percorre recursivamente dict/list/tuplas e retorna (path, string) para cada string encontrada.
    """
    if obj is None:
        return
    if isinstance(obj, str):
        yield path, obj
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _iter_strings(v, f"{path}.{k}")
        return
    if isinstance(obj, (list, tuple, set)):
        for i, v in enumerate(obj):
            yield from _iter_strings(v, f"{path}[{i}]")
        return


def assert_no_replacement_char(obj):
    """
    Asserta que não existe o caractere '�' em nenhuma string dentro do objeto (dict/list/str).
    """
    bad = []
    for p, s in _iter_strings(obj):
        if REPLACEMENT_CHAR in s:
            # mostra um trecho curto para debug
            idx = s.find(REPLACEMENT_CHAR)
            start = max(0, idx - 20)
            end = min(len(s), idx + 20)
            snippet = s[start:end].replace("\n", "\\n")
            bad.append((p, snippet))
    if bad:
        details = "\n".join([f"- {p}: ...{snip}..." for p, snip in bad])
        raise AssertionError(
            "Encontrado caractere inválido '�' (U+FFFD) em strings:\n" + details
        )


# ----------------------------
# EXEMPLO 1: testando função de normalização
# ----------------------------
def test_normalize_removes_replacement_char():
    from text_normalizer import normalize_text

    raw = "Texto bugado � com Ã§ e Â°"
    cleaned = normalize_text(raw)
    assert REPLACEMENT_CHAR not in cleaned, "normalize_text não removeu '�'."


# ----------------------------
# EXEMPLO 2: testando um payload de IA (dict)
# ----------------------------
def test_ai_payload_has_no_replacement_char():
    # Simule aqui o payload que você recebe do Gemini.
    # Na prática, substitua por uma chamada real ao seu parser / pipeline.
    payload = {
        "steps": [
            {
                "step_order": 1,
                "description": "Isolar a área",
                "hazard": "Queda de altura",
                "consequences": "Fraturas",
                "safeguards": "Sinalizar",
                "epis": ["Capacete"],
            }
        ]
    }

    # se algum campo tiver '�', o teste falha com caminho exato
    assert_no_replacement_char(payload)


# ----------------------------
# EXEMPLO 3: testando resposta da sua API (opcional)
# ----------------------------
@pytest.mark.skip(reason="Habilite quando tiver o client/URL de teste configurados")
def test_api_response_has_no_replacement_char(client):
    """
    Exemplo para FastAPI TestClient:
    client = TestClient(app)
    """
    resp = client.get("/v1/contract")
    assert resp.status_code == 200
    data = resp.json()
    assert_no_replacement_char(data)
