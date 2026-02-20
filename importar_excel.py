import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import select
from models import EPI, Perigo
from excel_contract import SCHEMA_VERSION, validate_epis_df, validate_perigos_df
from text_normalizer import normalize_text


def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def importar_epis(db: Session, caminho_excel: str) -> dict:
    df = pd.read_excel(caminho_excel)
    validate_epis_df(df)
    df = _norm_cols(df)

    criados = 0

    for _, row in df.iterrows():
        epi = str(row.get("epi")).strip() if row.get("epi") is not None else ""
        descricao = row.get("descricao")
        normas = row.get("normas")

        epi = normalize_text(epi, origin="excel", field="epi") or ""
        descricao = normalize_text(descricao, origin="excel", field="descricao")
        normas = normalize_text(normas, origin="excel", field="normas")

        if not epi:
            continue

        existe = db.execute(select(EPI).where(EPI.epi == epi)).scalar_one_or_none()
        if existe:
            continue

        db.add(EPI(epi=epi, descricao=descricao, normas=normas))
        criados += 1

    db.commit()
    return {"schema_version": SCHEMA_VERSION, "epis_inseridos": criados}


def importar_perigos(db: Session, caminho_excel: str) -> dict:
    df = pd.read_excel(caminho_excel)
    validate_perigos_df(df)
    df = _norm_cols(df)

    criados = 0

    for _, row in df.iterrows():
        perigo = str(row.get("perigo")).strip() if row.get("perigo") is not None else ""
        consequencias = row.get("consequencias")
        salvaguardas = row.get("salvaguardas")

        perigo = normalize_text(perigo, origin="excel", field="perigo") or ""
        consequencias = normalize_text(consequencias, origin="excel", field="consequencias")
        salvaguardas = normalize_text(salvaguardas, origin="excel", field="salvaguardas")

        if not perigo:
            continue

        existe = db.execute(select(Perigo).where(Perigo.perigo == perigo)).scalar_one_or_none()
        if existe:
            continue

        db.add(Perigo(perigo=perigo, consequencias=consequencias, salvaguardas=salvaguardas))
        criados += 1

    db.commit()
    return {"schema_version": SCHEMA_VERSION, "perigos_inseridos": criados}
