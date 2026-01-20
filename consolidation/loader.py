import pandas as pd
import re
import unicodedata
from typing import List


def _norm_colname(s: str) -> str:
    """Normaliza nome de coluna: lowercase, sem acento, sem espaços estranhos."""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))  # remove acentos
    s = re.sub(r"\s+", "_", s)          # espaços -> _
    s = re.sub(r"[^a-z0-9_]", "_", s)   # limpa caracteres
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def _split_lista(valor) -> List[str]:
    """Aceita ';' ou ',' como separador e remove vazios."""
    if pd.isna(valor):
        return []
    if not isinstance(valor, str):
        valor = str(valor)
    valor = valor.strip()
    if not valor:
        return []
    partes = re.split(r"[;,]", valor)  # separa por ; OU ,
    return [p.strip() for p in partes if p.strip()]


def carregar_perigos(caminho_arquivo: str):
    """
    Loader adaptativo de perigos.

    Normaliza para:
    - id
    - perigo
    - consequencias (list[str])
    - salvaguardas (list[str])
    """

    df = pd.read_excel(caminho_arquivo)

    # mapa: coluna_normalizada -> coluna_original
    colunas = {_norm_colname(c): c for c in df.columns}

    # aliases (o que pode vir no Excel -> campo padrão)
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
        "consequencia_s": "consequencias",

        # salvaguardas
        "salvaguardas": "salvaguardas",
        "salvaguarda": "salvaguardas",
        "salva_guarda": "salvaguardas",
        "salva_guardas": "salvaguardas",
        "medidas": "salvaguardas",
        "controles": "salvaguardas",
        "medidas_de_controle": "salvaguardas",
    }

    # encontra a coluna original correspondente a um "campo padrão"
    def achar_coluna_padrao(nome_padrao: str) -> str | None:
        for k_norm, col_original in colunas.items():
            if aliases.get(k_norm) == nome_padrao:
                return col_original
        return None

    col_id = achar_coluna_padrao("id")
    if not col_id:
        raise ValueError(
            f"Excel de perigos precisa conter a coluna 'id'. Colunas encontradas: {list(df.columns)}"
        )

    col_perigo = achar_coluna_padrao("perigo")
    col_conseq = achar_coluna_padrao("consequencias")
    col_salva = achar_coluna_padrao("salvaguardas")

    # fallback extra que você já usa:
    col_normas = colunas.get("normas")
    col_epi = colunas.get("epi")

    perigos = []

    for _, row in df.iterrows():
        perigo_id = int(row[col_id])

        # perigo (obrigatório de fato: se não achar, gera padrão)
        perigo_val = None
        if col_perigo and pd.notna(row[col_perigo]):
            perigo_val = str(row[col_perigo]).strip()

        if not perigo_val:
            perigo_val = f"Perigo {perigo_id}"

        consequencias = []
        if col_conseq and pd.notna(row[col_conseq]):
            consequencias = _split_lista(row[col_conseq])

        salvaguardas = []
        if col_salva and pd.notna(row[col_salva]):
            salvaguardas = _split_lista(row[col_salva])

        # fallback: normas / epi como salvaguarda
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
