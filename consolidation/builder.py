from typing import Dict, List, Any
from datetime import datetime


# ==============================
# BUILDER DO DOCUMENTO CANÔNICO
# ==============================

def construir_documento(
    atividades: List[Dict[str, Any]],
    epis: List[Dict[str, Any]],
    perigos: List[Dict[str, Any]],
    hashes: Dict[str, str],
) -> Dict[str, Any]:
    """
    Constrói o JSON técnico canônico da APR,
    pronto para PDF, IA e auditoria.
    """

    documentos = []

    epis_index = _indexar_por_id(epis, "id")
    perigos_index = _indexar_por_id(perigos, "id")

    for atividade in atividades:
        documento = _construir_documento_atividade(
            atividade=atividade,
            epis=epis_index,
            perigos=perigos_index,
            hashes=hashes,
        )
        documentos.append(documento)

    return {
        "tipo_documento": "APR",
        "versao_modelo": "1.0",
        "gerado_em": datetime.utcnow().isoformat() + "Z",
        "documentos": documentos,
    }


# ==============================
# CONSTRUÇÃO POR ATIVIDADE
# ==============================

def _construir_documento_atividade(
    atividade: Dict[str, Any],
    epis: Dict[int, Dict],
    perigos: Dict[int, Dict],
    hashes: Dict[str, str],
) -> Dict[str, Any]:

    passos = atividade.get("passos", [])

    passos_consolidados = [
        _construir_passo(passo, epis, perigos)
        for passo in sorted(passos, key=lambda p: p.get("ordem", 0))
    ]

    normas_base = _coletar_normas_base(passos_consolidados)

    # 🔑 NORMALIZAÇÃO DEFINITIVA DOS HASHES (LISTA, NÃO DICT)
    hashes_origem = [
        {"arquivo": nome, "hash": valor}
        for nome, valor in hashes.items()
    ] if isinstance(hashes, dict) else hashes

    return {
        "apr": {
            "atividade_id": atividade.get("id") or atividade.get("atividade_id"),
            "atividade": atividade.get("atividade"),
            "local": atividade.get("local"),
            "funcao": atividade.get("funcao"),
            "normas_base": normas_base,
        },
        "passos": passos_consolidados,
        "audit": {
            "hashes_origem": hashes_origem,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "origem": "excel_validado",
        },
    }


# ==============================
# CONSTRUÇÃO DE PASSOS
# ==============================

def _construir_passo(
    passo: Dict[str, Any],
    epis: Dict[int, Dict],
    perigos: Dict[int, Dict],
) -> Dict[str, Any]:

    perigos_consolidados = []
    for perigo_id in passo.get("perigos", []):
        try:
            perigo = perigos.get(int(perigo_id))
            if perigo:
                perigos_consolidados.append(perigo)
        except (ValueError, TypeError):
            continue

    epis_consolidados = []
    for epi_id in passo.get("epis", []):
        try:
            epi = epis.get(int(epi_id))
            if epi:
                epis_consolidados.append(epi)
        except (ValueError, TypeError):
            continue

    return {
        "ordem": passo.get("ordem"),
        "descricao": passo.get("descricao"),
        "perigos": perigos_consolidados,
        "riscos": passo.get("riscos", []),
        "consequencias": passo.get("consequencias", []),
        "medidas_controle": passo.get("medidas_controle", {}),
        "epis": epis_consolidados,
        "normas": passo.get("normas", []),
    }


# ==============================
# FUNÇÕES AUXILIARES
# ==============================

def _coletar_normas_base(passos: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    normas = {}

    for passo in passos:
        for norma in passo.get("normas", []):
            normas[norma] = norma

        for epi in passo.get("epis", []):
            for norma in epi.get("normas", []):
                normas[norma] = norma

    return [{"codigo": n, "titulo": n} for n in normas.keys()]


def _indexar_por_id(
    lista: List[Dict[str, Any]],
    campo_id: str,
) -> Dict[int, Dict[str, Any]]:
    index = {}
    for item in lista:
        try:
            index[int(item[campo_id])] = item
        except (KeyError, ValueError, TypeError):
            continue
    return index
