from typing import Dict, List, Any
from datetime import datetime


def _garantir_dict(atividades: Any) -> Dict[Any, Dict[str, Any]]:
    """
    Garante que atividades SEMPRE seja dict.
    - dict -> retorna
    - list -> converte para {"1": item1, "2": item2, ...}
    - None/outros -> {}
    """
    if atividades is None:
        return {}

    if isinstance(atividades, dict):
        return atividades

    if isinstance(atividades, list):
        out: Dict[Any, Dict[str, Any]] = {}
        for i, item in enumerate(atividades, start=1):
            if isinstance(item, dict):
                out[str(i)] = item
            else:
                out[str(i)] = {"atividade": str(item), "passos": []}
        return out

    return {}


def construir_documento(
    atividades: Any,  # <- aceita dict OU list
    epis: List[Dict[str, Any]],
    perigos: List[Dict[str, Any]],
    hashes: dict,
) -> dict:
    """
    Builder de domínio (APR).
    Produz estrutura rica, sem ambiguidade de tipo.
    """

    documentos = []

    # ✅ não perde as atividades se vierem como list
    atividades = _garantir_dict(atividades)

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
        if not isinstance(atividade, dict):
            continue

        passos_raw = atividade.get("passos", [])
        if not isinstance(passos_raw, list):
            passos_raw = []

        passos_finais = []

        for passo in passos_raw:
            if not isinstance(passo, dict):
                continue

            # garante listas
            epis_refs = passo.get("epis", [])
            perigos_refs = passo.get("perigos", [])

            if not isinstance(epis_refs, list):
                epis_refs = []
            if not isinstance(perigos_refs, list):
                perigos_refs = []

            passos_finais.append({
                "ordem": passo.get("ordem"),
                "descricao": passo.get("descricao"),
                "riscos": passo.get("riscos", []),
                "medidas_controle": passo.get("medidas_controle", []),
                "normas": passo.get("normas", []),

                # ✅ sempre lista de strings (nome do EPI ou fallback)
                "epis": [
                    str(epis_index.get(int(eid), {}).get("nome", eid))
                    for eid in epis_refs
                    if str(eid).isdigit()
                ],

                # ✅ seu loader de perigos cria "perigo" (não "descricao")
                "perigos": [
                    str(
                        perigos_index.get(int(pid), {}).get("perigo")
                        or perigos_index.get(int(pid), {}).get("descricao")
                        or pid
                    )
                    for pid in perigos_refs
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

    passos = atividade.get("passos", [])
    if not isinstance(passos, list):
        return []

    for passo in passos:
        if not isinstance(passo, dict):
            continue

        normas_raw = passo.get("normas", [])
        if not isinstance(normas_raw, list):
            continue

        for norma in normas_raw:
            if isinstance(norma, str):
                normas.add(norma)

    return sorted(normas)
