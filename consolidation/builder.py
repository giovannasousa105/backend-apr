from typing import Dict, List, Any
from datetime import datetime


def construir_documento(
    atividades: Dict[Any, Dict[str, Any]],
    epis: List[Dict[str, Any]],
    perigos: List[Dict[str, Any]],
    hashes: dict,
) -> dict:
    """
    Constrói o documento APR consolidado com passos normalizados.
    """

    documentos = []

    # ==========================
    # Garantias defensivas
    # ==========================
    if not isinstance(atividades, dict):
        atividades = {}

    if not isinstance(hashes, dict):
        hashes = {}

    # ==========================
    # Indexação (performance + segurança)
    # ==========================
    epis_index = {
        int(e.get("id", idx)): e
        for idx, e in enumerate(epis)
        if isinstance(e, dict)
    }

    perigos_index = {
        int(p.get("id", idx)): p
        for idx, p in enumerate(perigos)
        if isinstance(p, dict)
    }

    # ==========================
    # Construção dos documentos
    # ==========================
    for atividade in atividades.values():

        passos_brutos = atividade.get("passos", [])
        passos_consolidados = []

        for passo in passos_brutos:
            if isinstance(passo, dict):
                passos_consolidados.append(
                    _construir_passo(
                        passo=passo,
                        epis=epis_index,
                        perigos=perigos_index,
                    )
                )

        documentos.append({
            "apr": {
                "atividade_id": atividade.get("atividade_id"),
                "atividade": atividade.get("atividade"),
                "local": atividade.get("local"),
                "funcao": atividade.get("funcao"),
                "normas_base": _extrair_normas_base(atividade),
            },
            "passos": passos_consolidados,
            "audit": {
                "hashes_origem": hashes,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        })

    return {
        "tipo_documento": "APR",
        "versao_modelo": "1.0",
        "gerado_em": datetime.utcnow().isoformat() + "Z",
        "documentos": documentos,
    }


def _construir_passo(
    passo: Dict[str, Any],
    epis: Dict[int, Dict[str, Any]],
    perigos: Dict[int, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Consolida um passo individual com EPIs e Perigos resolvidos.
    """

    perigos_consolidados = []
    for pid in passo.get("perigos", []):
        try:
            pid = int(pid)
            if pid in perigos:
                perigos_consolidados.append(perigos[pid])
        except Exception:
            continue

    epis_consolidados = []
    for eid in passo.get("epis", []):
        try:
            eid = int(eid)
            if eid in epis:
                epis_consolidados.append(epis[eid])
        except Exception:
            continue

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
    Extrai lista única de normas a partir dos passos.
    Retorna apenas strings (seguro para API e PDF).
    """

    normas = set()

    for passo in atividade.get("passos", []):
        for norma in passo.get("normas", []):
            if isinstance(norma, str):
                normas.add(norma)

    return sorted(normas)
