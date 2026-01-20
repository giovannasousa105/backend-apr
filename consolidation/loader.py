from __future__ import annotations

from typing import Any, Dict, List
import pandas as pd
import re
import unicodedata


# ==================================================
# NORMALIZAÇÃO
# ==================================================

def _norm_colname(s: str) -> str:
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))  # remove acentos
    s = re.sub(r"\s+", "_", s)          # espaços -> _
    s = re.sub(r"[^a-z0-9_]", "_", s)   # limpa caracteres
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def _split_lista(valor) -> List[str]:
    if pd.isna(valor):
        return []
    if not isinstance(valor, str):
        valor = str(valor)
    partes = re.split(r"[;,]", valor)
    return [p.strip() for p in partes if p.strip()]


# ==================================================
# LOADER: EPIs
# ==================================================

def carregar_epis(caminho_arquivo: str) -> List[Dict[str, Any]]:
    """
    Loader adaptativo de EPIs.
    Normaliza para:
    { id: int, nome: str, tipo: str|None }
    """
    df = pd.read_excel(caminho_arquivo)
    colunas = {_norm_colname(c): c for c in df.columns}

    if "id" not in colunas:
        raise ValueError("Excel de EPIs precisa conter a coluna 'id'")

    epis: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        epi_id = int(row[colunas["id"]])

        nome = None
        for campo in ["epi", "nome", "descricao"]:
            if campo in colunas and pd.notna(row[colunas[campo]]):
                nome = str(row[colunas[campo]]).strip()
                break

        tipo = None
        if "tipo" in colunas and pd.notna(row[colunas["tipo"]]):
            tipo = str(row[colunas["tipo"]]).strip()

        epis.append({
            "id": epi_id,
            "nome": nome or f"EPI {epi_id}",
            "tipo": tipo,
        })

    return epis


# ==================================================
# LOADER: PERIGOS
# ==================================================

def carregar_perigos(caminho_arquivo: str) -> List[Dict[str, Any]]:
    """
    Loader adaptativo de perigos.
    Normaliza para:
    - id
    - perigo
    - consequencias (list[str])
    - salvaguardas (list[str])
    """
    df = pd.read_excel(caminho_arquivo)
    colunas = {_norm_colname(c): c for c in df.columns}

    aliases = {
        # id
        "id": "id",
        "codigo": "id",
        "cod": "id",

        # perigo
        "perigo": "perigo",
        "title": "perigo",
        "titulo": "perigo",
        "descricao": "perigo",
        "descr": "perigo",

        # consequencias
        "consequencias": "consequencias",
        "consequencia": "consequencias",

        # salvaguardas
        "salvaguardas": "salvaguardas",
        "salvaguarda": "salvaguardas",
        "salva_guarda": "salvaguardas",
        "salva_guardas": "salvaguardas",
        "medidas": "salvaguardas",
        "controles": "salvaguardas",
        "medidas_de_controle": "salvaguardas",
    }

    def achar_coluna(padrao: str) -> str | None:
        for norm, original in colunas.items():
            if aliases.get(norm) == padrao:
                return original
        return None

    col_id = achar_coluna("id")
    if not col_id:
        raise ValueError("Excel de perigos precisa conter a coluna 'id'")

    col_perigo = achar_coluna("perigo")
    col_conseq = achar_coluna("consequencias")
    col_salva = achar_coluna("salvaguardas")

    # fallbacks extras
    col_normas = colunas.get("normas")
    col_epi = colunas.get("epi")

    perigos: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        perigo_id = int(row[col_id])

        perigo_val = None
        if col_perigo and pd.notna(row[col_perigo]):
            perigo_val = str(row[col_perigo]).strip()
        if not perigo_val:
            perigo_val = f"Perigo {perigo_id}"

        consequencias = _split_lista(row[col_conseq]) if (col_conseq and pd.notna(row[col_conseq])) else []
        salvaguardas = _split_lista(row[col_salva]) if (col_salva and pd.notna(row[col_salva])) else []

        if not salvaguardas:
            if col_normas and pd.notna(row[col_normas]):
                salvaguardas = _split_lista(row[col_normas])
            elif col_epi and pd.notna(row[col_epi]):
                salvaguardas = _split_lista(row[col_epi])

        perigos.append({
            "id": perigo_id,
            "perigo": perigo_val,
            "consequencias": consequencias,
            "salvaguardas": salvaguardas,
        })

    return perigos
