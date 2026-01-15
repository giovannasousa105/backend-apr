import pandas as pd
from sqlalchemy.orm import Session
from models import APR, Passo


def importar_apr_excel(file_path: str, db: Session):
    df = pd.read_excel(file_path)

    # Cria APR
    apr = APR(
        titulo=df["Atividade"].iloc[0],
        descricao="Importada do Excel",
        risco="Médio"
    )

    db.add(apr)
    db.commit()
    db.refresh(apr)

    # Cria Passos
    for _, row in df.iterrows():
        passo = Passo(
            apr_id=apr.id,
            ordem=int(row["Passo"]),
            descricao=row["Descrição"],
            perigos=row.get("Perigos", ""),
            riscos=row.get("Riscos", ""),
            medidas_controle=row.get("Medidas de Controle", ""),
            epis=row.get("EPIs", ""),
            normas=row.get("Normas", "")
        )

        db.add(passo)

    db.commit()
    return apr
