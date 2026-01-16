import pandas as pd
from sqlalchemy.orm import Session
import models


def importar_apr_excel(caminho_arquivo: str, db: Session):
    df = pd.read_excel(caminho_arquivo)

    if df.empty:
        raise ValueError("Arquivo Excel vazio")

    # pega dados da APR da primeira linha
    titulo = df.loc[0, "titulo_apr"]
    risco = df.loc[0, "risco"]
    descricao_apr = df.loc[0, "descricao_apr"]

    apr = models.APR(
        titulo=titulo,
        risco=risco,
        descricao=descricao_apr
    )

    db.add(apr)
    db.flush()  # 🔴 cria ID sem commit

    for _, row in df.iterrows():
        passo = models.Passo(
            descricao=row["passo_descricao"],
            apr_id=apr.id
        )
        db.add(passo)

    db.commit()
    db.refresh(apr)

    return apr

