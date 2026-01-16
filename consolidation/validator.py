from typing import Dict, List


class ValidationError(Exception):
    """
    Erro de validação técnica do documento.
    """
    pass


# ==============================
# VALIDATOR PRINCIPAL
# ==============================

def validar_documento(
    atividades: Dict,
    epis: Dict[int, Dict],
    perigos: Dict[int, Dict]
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

    for atividade_id, atividade in atividades.items():
        _validar_atividade(atividade_id, atividade, epis, perigos)


# ==============================
# VALIDAÇÕES ESPECÍFICAS
# ==============================

def _validar_atividade(
    atividade_id: str,
    atividade: Dict,
    epis: Dict[int, Dict],
    perigos: Dict[int, Dict]
):
    if not atividade.get("passos"):
        raise ValidationError(
            f"Atividade '{atividade_id}' não possui passos definidos"
        )

    ordens = []

    for passo in atividade["passos"]:
        _validar_passo(atividade_id, passo, epis, perigos)
        ordens.append(passo["ordem"])

    # Verifica ordem sequencial
    if sorted(ordens) != list(range(1, len(ordens) + 1)):
        raise ValidationError(
            f"Ordem dos passos inválida na atividade '{atividade_id}'"
        )


def _validar_passo(
    atividade_id: str,
    passo: Dict,
    epis: Dict[int, Dict],
    perigos: Dict[int, Dict]
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
        tipo="EPI"
    )

    _validar_referencias(
        atividade_id=atividade_id,
        ordem=ordem,
        referencias=passo.get("perigos", []),
        cadastro=perigos,
        tipo="Perigo"
    )


def _validar_referencias(
    atividade_id: str,
    ordem: int,
    referencias: List,
    cadastro: Dict[int, Dict],
    tipo: str
):
    for ref in referencias:
        try:
            ref_id = int(ref)
        except ValueError:
            raise ValidationError(
                f"{tipo} inválido '{ref}' no passo {ordem} da atividade '{atividade_id}'"
            )

        if ref_id not in cadastro:
            raise ValidationError(
                f"{tipo} ID {ref_id} não encontrado no cadastro "
                f"(passo {ordem}, atividade '{atividade_id}')"
            )
