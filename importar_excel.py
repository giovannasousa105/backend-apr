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


def _parse_default_factor(value) -> int:
    if value is None:
        return 0
    try:
        parsed = int(value)
    except Exception:
        return 0
    if parsed < 0:
        return 0
    if parsed > 5:
        return 5
    return parsed


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
    atualizados = 0

    for _, row in df.iterrows():
        perigo = str(row.get("perigo")).strip() if row.get("perigo") is not None else ""
        consequencias = row.get("consequencias")
        salvaguardas = row.get("salvaguardas")
        default_probability = _parse_default_factor(row.get("default_probability"))
        default_severity = _parse_default_factor(row.get("default_severity"))

        perigo = normalize_text(perigo, origin="excel", field="perigo") or ""
        consequencias = normalize_text(consequencias, origin="excel", field="consequencias")
        salvaguardas = normalize_text(salvaguardas, origin="excel", field="salvaguardas")

        if not perigo:
            continue

        existe = db.execute(select(Perigo).where(Perigo.perigo == perigo)).scalar_one_or_none()
        if existe:
            changed = False
            if (not existe.consequencias) and consequencias:
                existe.consequencias = consequencias
                changed = True
            if (not existe.salvaguardas) and salvaguardas:
                existe.salvaguardas = salvaguardas
                changed = True
            if _parse_default_factor(existe.default_probability) == 0 and default_probability > 0:
                existe.default_probability = default_probability
                changed = True
            if _parse_default_factor(existe.default_severity) == 0 and default_severity > 0:
                existe.default_severity = default_severity
                changed = True
            if changed:
                atualizados += 1
            continue

        db.add(
            Perigo(
                perigo=perigo,
                consequencias=consequencias,
                salvaguardas=salvaguardas,
                default_probability=default_probability,
                default_severity=default_severity,
            )
        )
        criados += 1

    db.commit()
    return {
        "schema_version": SCHEMA_VERSION,
        "perigos_inseridos": criados,
        "perigos_atualizados": atualizados,
    }
