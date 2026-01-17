import pandas as pd
from typing import Dict, List


# ==================================================
# FUNÇÃO AUXILIAR
# ==================================================

def _parse_lista(valor) -> List[str]:
    """
    Converte célula do Excel em lista de strings.
    Aceita:
    - valores separados por vírgula
    - valor único
    - NaN
    """
    if pd.isna(valor):
        return []

    if isinstance(valor, str):
        return [item.strip() for item in valor.split(",") if item.strip()]

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
# LOADER: ATIVIDADES / PASSOS
# ==================================================

def carregar_atividades_passos(caminho_atividades: str) -> Dict[str, Dict]:
    """
    Excel esperado:
    atividade_id | atividade | local | funcao |
    ordem_passo | descricao_passo |
    perigos | riscos | medidas_controle | epis | normas
    """
    df = pd.read_excel(caminho_atividades)

    colunas = {
        "atividade_id",
        "atividade",
        "local",
        "funcao",
        "ordem_passo",
        "descricao_passo",
        "perigos",
        "riscos",
        "medidas_controle",
        "epis",
        "normas",
    }

    if not colunas.issubset(df.columns):
        raise ValueError(
            f"Excel de Atividades inválido. Esperado {colunas}. Encontrado {set(df.columns)}"
        )

    atividades = {}

    for _, row in df.iterrows():
        atividade_id = str(row["atividade_id"]).strip()

        if atividade_id not in atividades:
            atividades[atividade_id] = {
                "atividade_id": atividade_id,
                "atividade": str(row["atividade"]).strip(),
                "local": str(row["local"]).strip(),
                "funcao": str(row["funcao"]).strip(),
                "passos": [],
            }

        passo = {
            "ordem": int(row["ordem_passo"]),
            "descricao": str(row["descricao_passo"]).strip(),
            "perigos": _parse_lista(row["perigos"]),
            "riscos": _parse_lista(row["riscos"]),
            "medidas_controle": _parse_lista(row["medidas_controle"]),
            "epis": _parse_lista(row["epis"]),
            "normas": _parse_lista(row["normas"]),
        }

        atividades[atividade_id]["passos"].append(passo)

    return atividades
