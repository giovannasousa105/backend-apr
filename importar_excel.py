import pandas as pd
from sqlalchemy.orm import Session
import models


COLUNAS_OBRIGATORIAS = [
    "titulo_apr",
    "risco",
    "descricao_apr",
    "passo_descricao"
]


def importar_apr_excel(caminho_arquivo: str, db: Session):

    try:
        df = pd.read_excel(caminho_arquivo)
    except Exception:
        raise ValueError("Não foi possível ler o arquivo Excel")

    # 1️⃣ Excel vazio
    if df.empty:
        raise ValueError("O arquivo Excel está vazio")

    # 2️⃣ Verificar colunas obrigatórias
    for coluna in COLUNAS_OBRIGATORIAS:
        if coluna not in df.columns:
            raise ValueError(f"Coluna obrigatória ausente: '{coluna}'")

    # 3️⃣ Verificar células vazias
    for index, row in df.iterrows():
        linha_excel = index + 2  # +2 por causa do cabeçalho
        for coluna in COLUNAS_OBRIGATORIAS:
            if pd.isna(row[coluna]) or str(row[coluna]).strip() == "":
                raise ValueError(
                    f"Valor vazio na coluna '{coluna}' (linha {linha_excel})"
                )

    # 4️⃣ Criar APR (primeira linha)
    titulo = str(df.loc[0, "titulo_apr"]).strip()
    risco = str(df.loc[0, "risco"]).strip()
    descricao_apr = str(df.loc[0, "descricao_apr"]).strip()

    apr = models.APR(
        titulo=titulo,
        risco=risco,
        descricao=descricao_apr
    )

    db.add(apr)
    db.flush()  # cria ID sem commit

    # 5️⃣ Criar Passos
    for _, row in df.iterrows():
        passo = models.Passo(
            descricao=str(row["passo_descricao"]).strip(),
            apr_id=apr.id
        )
        db.add(passo)

    db.commit()
    db.refresh(apr)

    return apr
