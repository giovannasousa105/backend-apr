import pandas as pd
from typing import Dict, List


# ==============================
# LOADER DOS EXCELS VALIDADO
# ==============================

def carregar_epis(caminho_epis: str) -> Dict[int, Dict]:
    """
    Lê o Excel de EPIs e retorna um dicionário indexado por ID.
    """
    df = pd.read_excel(caminho_epis)

    epis = {}

    for _, row in df.iterrows():
        epi_id = int(row["id"])
        epis[epi_id] = {
            "id": epi_id,
            "epi": str(row["epi"]).strip(),
            "descricao": str(row["descricao"]).strip(),
            "normas": _parse_lista(row.get("normas"))
        }

    return epis


def carregar_perigos(caminho_perigos: str) -> Dict[int, Dict]:
    """
    Lê o Excel de Perigos e retorna um dicionário indexado por ID.
    """
    df = pd.read_excel(caminho_perigos)

    perigos = {}

    for _, row in df.iterrows():
        perigo_id = int(row["id"])
        perigos[perigo_id] = {
            "id": perigo_id,
            "perigo": str(row["perigo"]).strip(),
            "consequencias": _parse_lista(row.get("consequencias")),
            "salvaguardas": _parse_lista(row.get("salvaguardas"))
        }

    return perigos


def carregar_atividades_passos(caminho_atividades: str) -> Dict:
    """
    Lê o Excel de Atividades/Passos e retorna estrutura bruta organizada.
    """
    df = pd.read_excel(caminho_atividades)

    atividades = {}

    for _, row in df.iterrows():
        atividade_id = str(row["atividade_id"]).strip()

        if atividade_id not in atividades:
            atividades[atividade_id] = {
                "atividade_id": atividade_id,
                "atividade": str(row["atividade"]).strip(),
                "local": str(row["local"]).strip(),
                "funcao": str(row["funcao"]).strip(),
                "passos": []
            }

        passo = {
            "ordem": int(row["ordem_passo"]),
            "descricao": str(row["descricao_passo"]).strip(),
            "perigos": _parse_lista(row.get("perigos")),
            "riscos": _parse_lista(row.get("riscos")),
            "medidas_controle": _parse_lista(row.get("medidas_controle")),
            "epis": _parse_lista(row.get("epis")),
            "normas": _parse_lista(row.get("normas"))
        }

        atividades[atividade_id]["passos"].append(passo)

    return atividades


# ==============================
# FUNÇÕES AUXILIARES
# ==============================

def _parse_lista(valor) -> List:
    """
    Converte célula do Excel em lista.
    Aceita:
    - valores separados por vírgula
    - valores únicos
    - NaN
    """
    if pd.isna(valor):
        return []

    if isinstance(valor, str):
        return [item.strip() for item in valor.split(",") if item.strip()]

    return [str(valor).strip()]
