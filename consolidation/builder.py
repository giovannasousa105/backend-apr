from typing import Dict, List, Any
from datetime import datetime


def construir_documento(
    atividades: Dict[Any, Dict[str, Any]],
    epis: List[Dict[str, Any]],
    perigos: List[Dict[str, Any]],
    hashes: dict,
) -> dict:
    """
    Builder de domínio (APR).
    Produz estrutura rica, mas SEM ambiguidade de tipo.
    """

    documentos = []

    if not isinstance(atividades, dict):
        atividades = {}

    if not isinstance(hashes, dict):
        hashes = {}

    # Indexação segura
    epis_index = {
        int(e.get("id", i)): e
        for i, e in enumerate(epis)
        if isinstance(e, dict)
    }

    perigos_index = {
        int(p.get("id", i)): p
        for i, p in enumerate(perigos)
        if isinstance(p, dict)
    }

    for atividade in atividades.values():

        passos_finais = []

        for passo in atividade.get("passos", []):
            if not isinstance(passo, dict):
                continue

            passos_finais.append({
                "ordem": passo.get("ordem"),
                "descricao": passo.get("descricao"),
                "riscos": passo.get("riscos", []),
                "medidas_controle": passo.get("medidas_controle", []),
                "normas": passo.get("normas", []),

                # 👇 AQUI É O PONTO CRÍTICO: SEMPRE LISTA DE STRINGS
                "epis": [
                    str(epis_index.get(int(eid), {}).get("nome", eid))
                    for eid in passo.get("epis", [])
                    if str(eid).isdigit()
                ],

                "perigos": [
                    str(perigos_index.get(int(pid), {}).get("descricao", pid))
                    for pid in passo.get("perigos", [])
                    if str(pid).isdigit()
                ],
            })

        documentos.append({
            "apr": {
                "atividade_id": atividade.get("atividade_id"),
                "atividade": atividade.get("atividade"),
                "local": atividade.get("local"),
                "funcao": atividade.get("funcao"),
                "normas_base": _extrair_normas_base(atividade),
            },
            "passos": passos_finais,
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


def _extrair_normas_base(atividade: Dict[str, Any]) -> List[str]:
    normas = set()

    for passo in atividade.get("passos", []):
        for norma in passo.get("normas", []):
            if isinstance(norma, str):
                normas.add(norma)

    return sorted(normas)
