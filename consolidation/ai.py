from typing import List, Dict, Any


def gerar_atividades_por_ai(
    perigos: Dict[int, Dict[str, Any]],
    epis: Dict[int, Dict[str, Any]],
) -> List[Dict[str, Any]]:

    atividade = {
        "atividade_id": 1,
        "atividade": "Atividade gerada automaticamente",
        "local": "Não informado",
        "funcao": "Não informada",
        "passos": [],
    }

    epis_ids = list(epis.keys())

    for ordem, perigo in enumerate(perigos.values(), start=1):
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
            "riscos": perigo.get("consequencias", []),
            "consequencias": perigo.get("consequencias", []),
            "medidas_controle": medidas_controle,
            "epis": epis_ids,
            "normas": [],
        }

        atividade["passos"].append(passo)

    return [atividade]
