# consolidation/ai.py

from typing import Dict, List, Any


def gerar_atividades_por_ai(
    perigos: List[Dict[str, Any]],
    epis: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Gera atividades e passos de forma controlada.
    (Stub seguro – não chama OpenAI ainda)
    """

    atividade = {
        "id": 1,
        "atividade": "Atividade gerada automaticamente",
        "local": "Não informado",
        "funcao": "Não informada",
        "passos": []
    }

    # cria lista de IDs de EPIs
    epis_ids = []
    for epi in epis:
        if "id" in epi:
            try:
                epis_ids.append(int(epi["id"]))
            except (ValueError, TypeError):
                continue

    # gera um passo por perigo
    for ordem, perigo in enumerate(perigos, start=1):
        perigo_id = perigo.get("id")

        if perigo_id is None:
            continue

        passo = {
            "ordem": ordem,
            "descricao": f"Tratativa do perigo: {perigo.get('perigo', 'Perigo não informado')}",
            "perigos": [perigo_id],
            "riscos": perigo.get("consequencias", []),
            "medidas_controle": perigo.get("salvaguardas", []),
            "epis": epis_ids,
            "normas": []
        }

        atividade["passos"].append(passo)

    return [atividade]
