# consolidation/ai.py

from typing import Dict, List


def gerar_atividades_por_ai(perigos: Dict[int, Dict], epis: Dict[int, Dict]) -> List[Dict]:
    """
    Gera atividades e passos de forma controlada.
    (Stub seguro – não chama OpenAI ainda)
    """

    atividade = {
        "atividade_id": 1,
        "atividade": "Atividade gerada automaticamente",
        "local": "Não informado",
        "funcao": "Não informada",
        "passos": []
    }

    for ordem, perigo in enumerate(perigos.values(), start=1):
        passo = {
            "ordem": ordem,
            "descricao": f"Tratativa do perigo: {perigo['perigo']}",
            "perigos": [perigo["id"]],
            "riscos": perigo.get("consequencias", []),
            "medidas_controle": perigo.get("salvaguardas", []),
            "epis": list(epis.keys()),
            "normas": []
        }

        atividade["passos"].append(passo)

    return [atividade]
