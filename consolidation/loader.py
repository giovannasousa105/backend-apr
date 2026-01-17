import pandas as pd
from typing import Dict, List


# ==================================================
# FUNÇÃO AUXILIAR
# ==================================================

def _parse_lista(valor) -> List[str]:
    if pd.isna(valor):
        return []
    if isinstance(valor, str):
        return [v.strip() for v in valor.split(",") if v.strip()]
    return [str(valor).strip()]


# ==================================================
# LOADER: EPIs
# ==================================================

def carregar_epis(caminho_epis: str) -> Dict[int, Dict]:
    """
    Excel esperado:
    id | epi | descricao | normas
    """
    df = pd.read_excel(caminho_epis)

    colunas = {"id", "epi", "descricao", "normas"}
    if not colunas.issubset(df.columns):
        raise ValueError(
            f"Excel de EPIs inválido. Esperado {colunas}. Encontrado {set(df.columns)}"
        )

    epis = {}

    for _, row in df.iterrows():
        epi_id = int(row["id"])

        epis[epi_id] = {
            "id": epi_id,
            "epi": str(row["epi"]).strip(),
            "descricao": str(row["descricao"]).strip(),
            "normas": _parse_lista(row["normas"]),
        }

    return epis


# ==================================================
# LOADER: PERIGOS
# ==================================================

def carregar_perigos(caminho_perigos: str) -> Dict[int, Dict]:
    """
    Excel esperado:
    id | perigo | consequencias | salvaguardas
    """
    df = pd.read_excel(caminho_perigos)

    colunas = {"id", "perigo", "consequencias", "salvaguardas"}
    if not colunas.issubset(df.columns):
        raise ValueError(
            f"Excel de Perigos inválido. Esperado {colunas}. Encontrado {set(df.columns)}"
        )

    perigos = {}

    for _, row in df.iterrows():
        perigo_id = int(row["id"])

        perigos[perigo_id] = {
            "id": perigo_id,
            "perigo": str(row["perigo"]).strip(),
            "consequencias": _parse_lista(row["consequencias"]),
            "salvaguardas": _parse_lista(row["salvaguardas"]),
        }

    return perigos


# ==================================================
# BUILDER: ATIVIDADE + PASSOS (GERADO)
# ==================================================

def construir_atividades(perigos: Dict[int, Dict], epis: Dict[int, Dict]) -> List[Dict]:
    """
    Gera automaticamente:
    - 1 atividade
    - 1 passo por perigo
    """
    atividade = {
        "atividade_id": 1,
        "atividade": "Atividade gerada automaticamente",
        "local": "Não especificado",
        "funcao": "Não especificada",
        "passos": [],
    }

    for idx, perigo in enumerate(perigos.values(), start=1):
        passo = {
            "ordem": idx,
            "descricao": f"Controle do perigo: {perigo['perigo']}",
            "perigos": [perigo["id"]],
            "epis": list(epis.keys()),
            "riscos": perigo["consequencias"],
            "medidas_controle": perigo["salvaguardas"],
            "normas": [],
        }

        atividade["passos"].append(passo)

    return [atividade]
