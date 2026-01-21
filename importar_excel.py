import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import select

from models import EPI, Perigo


def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def importar_epis(db: Session, caminho_excel: str) -> dict:
    df = pd.read_excel(caminho_excel)
    df = _norm_cols(df)

    # ASCII-only candidates (no accents)
    col = _pick_col(df, ["epi", "epis", "nome", "equipamento", "equipamento de protecao"])
    if col is None:
        col = df.columns[0] if len(df.columns) else None

    if col is None:
        return {"epis_inseridos": 0, "erro": "Nenhuma coluna encontrada no Excel"}

    criados = 0
    for val in df[col].dropna().astype(str):
        nome = val.strip()
        if not nome:
            continue

        existe = db.execute(select(EPI).where(EPI.nome == nome)).scalar_one_or_none()
        if existe:
            continue

        db.add(EPI(nome=nome))
        criados += 1

    db.commit()
    return {"epis_inseridos": criados}


def importar_perigos(db: Session, caminho_excel: str) -> dict:
    df = pd.read_excel(caminho_excel)
    df = _norm_cols(df)

    col = _pick_col(df, ["perigo", "perigos", "hazard", "nome"])
    if col is None:
        col = df.columns[0] if len(df.columns) else None

    if col is None:
        return {"perigos_inseridos": 0, "erro": "Nenhuma coluna encontrada no Excel"}

    criados = 0
    for val in df[col].dropna().astype(str):
        nome = val.strip()
        if not nome:
            continue

        existe = db.execute(select(Perigo).where(Perigo.nome == nome)).scalar_one_or_none()
        if existe:
            continue

        db.add(Perigo(nome=nome))
        criados += 1

    db.commit()
    return {"perigos_inseridos": criados}
