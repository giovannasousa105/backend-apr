import pandas as pd
from typing import Dict, List, Any


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

def carregar_epis(caminho_epis: str) -> List[Dict[str, Any]]:
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

    epis: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        epi_id = int(row["id"])

        epis.append({
            "id": epi_id,
            "epi": str(row["epi"]).strip(),
            "descricao": str(row["descricao"]).strip(),
            "normas": _parse_lista(row["normas"]),
        })

    return epis


# ==================================================
# LOADER: PERIGOS
# ==================================================

def carregar_perigos(caminho_perigos: str) -> List[Dict[str, Any]]:
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

    perigos: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        perigo_id = int(row["id"])

        perigos.append({
            "id": perigo_id,
            "perigo": str(row["perigo"]).strip(),
            "consequencias": _parse_lista(row["consequencias"]),
            "salvaguardas": _parse_lista(row["salvaguardas"]),
        })

    return perigos
