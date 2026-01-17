from typing import Dict, List, Any


class ValidationError(Exception):
    """
    Erro de validação técnica do documento.
    """
    pass


# ==============================
# VALIDATOR PRINCIPAL
# ==============================

def validar_documento(
    atividades: List[Dict[str, Any]],
    epis: List[Dict[str, Any]],
    perigos: List[Dict[str, Any]],
):
    """
    Valida consistência técnica entre:
    - Atividades/Passos
    - EPIs
    - Perigos
    """

    if not atividades:
        raise ValidationError("Nenhuma atividade encontrada")

    if not epis:
        raise ValidationError("Cadastro de EPIs vazio")

    if not perigos:
        raise ValidationError("Cadastro de perigos vazio")

    # cria índices rápidos por ID
    epis_index = _indexar_por_id(epis, "id")
    perigos_index = _indexar_por_id(perigos, "id")

    for atividade in atividades:
        atividade_id = atividade.get("id") or atividade.get("nome") or "atividade_sem_id"
        _validar_atividade(
            atividade_id=atividade_id,
            atividade=atividade,
            epis=epis_index,
            perigos=perigos_index,
        )


# ==============================
# VALIDAÇÕES ESPECÍFICAS
# ==============================

def _validar_atividade(
    atividade_id: str,
    atividade: Dict[str, Any],
    epis: Dict[int, Dict],
    perigos: Dict[int, Dict],
):
    passos = atividade.get("passos")

    if not passos or not isinstance(passos, list):
        raise ValidationError(
            f"Atividade '{atividade_id}' não possui passos definidos"
        )

    ordens = []

    for passo in passos:
        _validar_passo(atividade_id, passo, epis, perigos)
        ordens.append(passo.get("ordem"))

    # Verifica ordem sequencial (1,2,3...)
    if sorted(ordens) != list(range(1, len(ordens) + 1)):
        raise ValidationError(
            f"Ordem dos passos inválida na atividade '{atividade_id}'"
        )


def _validar_passo(
    atividade_id: str,
    passo: Dict[str, Any],
    epis: Dict[int, Dict],
    perigos: Dict[int, Dict],
):
    ordem = passo.get("ordem")

    if ordem is None:
        raise ValidationError(
            f"Passo sem ordem definida na atividade '{atividade_id}'"
        )

    if not passo.get("descricao"):
        raise ValidationError(
            f"Descrição vazia no passo {ordem} da atividade '{atividade_id}'"
        )

    _validar_referencias(
        atividade_id=atividade_id,
        ordem=ordem,
        referencias=passo.get("epis", []),
        cadastro=epis,
        tipo="EPI",
    )

    _validar_referencias(
        atividade_id=atividade_id,
        ordem=ordem,
        referencias=passo.get("perigos", []),
        cadastro=perigos,
        tipo="Perigo",
    )


def _validar_referencias(
    atividade_id: str,
    ordem: int,
    referencias: List[Any],
    cadastro: Dict[int, Dict],
    tipo: str,
):
    for ref in referencias:
        try:
            ref_id = int(ref)
        except (ValueError, TypeError):
            raise ValidationError(
                f"{tipo} inválido '{ref}' no passo {ordem} da atividade '{atividade_id}'"
            )

        if ref_id not in cadastro:
            raise ValidationError(
                f"{tipo} ID {ref_id} não encontrado no cadastro "
                f"(passo {ordem}, atividade '{atividade_id}')"
            )


# ==============================
# UTIL
# ==============================

def _indexar_por_id(lista: List[Dict[str, Any]], campo_id: str) -> Dict[int, Dict]:
    """
    Converte lista de dicts em dict indexado por ID.
    Ex: [{id:1},{id:2}] -> {1:{...}, 2:{...}}
    """
    index = {}
    for item in lista:
        if campo_id not in item:
            continue
        try:
            index[int(item[campo_id])] = item
        except (ValueError, TypeError):
            continue
    return index
