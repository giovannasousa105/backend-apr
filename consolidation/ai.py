from typing import List, Dict, Any


def gerar_atividades_por_ai(
    perigos: List[Dict[str, Any]],
    epis: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    atividade = {
        "id": 1,
        "atividade": "Atividade gerada automaticamente",
        "local": "Não informado",
        "funcao": "Não informada",
        "passos": []
    }

    epis_ids: List[int] = []
    for epi in epis:
        if "id" in epi:
            try:
                epis_ids.append(int(epi["id"]))
            except (ValueError, TypeError):
                continue

    for ordem, perigo in enumerate(perigos, start=1):
        perigo_id = perigo.get("id")
        if perigo_id is None:
            continue

        medidas_controle = {
            "eliminacao": [],
            "substituicao": [],
            "engenharia": perigo.get("salvaguardas", []),
            "administrativa": [],
            "epi": epis_ids,
        }

        passo = {
            "ordem": ordem,
            "descricao": f"Execução segura relacionada ao perigo: {perigo.get('perigo')}",
            "perigos": [perigo_id],
            "riscos": perigo.get("riscos", []),
            "consequencias": perigo.get("consequencias", []),
            "medidas_controle": medidas_controle,
            "epis": epis_ids,
            "normas": []
        }

        atividade["passos"].append(passo)

    return [atividade]
