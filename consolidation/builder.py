from typing import Dict, List, Any
from datetime import datetime


def construir_documento(
    atividades: dict,   # 🔑 AGORA É DICT
    epis: list,
    perigos: list,
    hashes: dict,
) -> dict:

    documentos = []

    for atividade in atividades.values():  # 👈 FIX
        documentos.append({
            "apr": {
                "atividade_id": atividade.get("atividade_id"),
                "atividade": atividade.get("atividade"),
                "local": atividade.get("local"),
                "funcao": atividade.get("funcao"),
                "normas_base": [],
            },
            "passos": atividade.get("passos", []),
            "audit": {
                "hashes_origem": hashes,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        })

    return {
        "tipo_documento": "APR",
        "documentos": documentos,
    }

    # 🔒 GARANTIA ABSOLUTA DE DICT
    if isinstance(hashes, list):
        hashes = {f"arquivo_{i}": v for i, v in enumerate(hashes)}
    elif not isinstance(hashes, dict):
        hashes = {}

    for atividade in atividades:
        documentos.append(
            _construir_documento_atividade(
                atividade=atividade,
                epis=epis_index,
                perigos=perigos_index,
                hashes=hashes
            )
        )

    return {
        "tipo_documento": "APR",
        "versao_modelo": "1.0",
        "gerado_em": datetime.utcnow().isoformat() + "Z",
        "documentos": documentos
    }


def _construir_passo(
    passo: Dict[str, Any],
    epis: Dict[int, Dict[str, Any]],
    perigos: Dict[int, Dict[str, Any]],
) -> Dict[str, Any]:

    perigos_consolidados = []
    for pid in passo.get("perigos", []):
        pid = int(pid)
        if pid in perigos:
            perigos_consolidados.append(perigos[pid])

    epis_consolidados = []
    for eid in passo.get("epis", []):
        eid = int(eid)
        if eid in epis:
            epis_consolidados.append(epis[eid])

    return {
        "ordem": passo.get("ordem"),
        "descricao": passo.get("descricao"),
        "perigos": perigos_consolidados,
        "riscos": passo.get("riscos", []),
        "medidas_controle": passo.get("medidas_controle", []),
        "epis": epis_consolidados,
        "normas": passo.get("normas", []),
    }


def _extrair_normas_base(atividade: Dict[str, Any]) -> List[str]:
    """
    Retorna apenas lista simples de normas (SEM dicts)
    """

    normas = set()

    for passo in atividade.get("passos", []):
        for norma in passo.get("normas", []):
            if isinstance(norma, str):
                normas.add(norma)

    return sorted(normas)
