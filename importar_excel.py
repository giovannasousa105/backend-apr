import pandas as pd
from database import SessionLocal
from models import Atividade, Passo, Epi, Perigo

db = SessionLocal()

# =========================
# IMPORTAR PERIGOS
# =========================
df_perigos = pd.read_excel("perigos_apr_modelo_validado.xlsx")

for _, row in df_perigos.iterrows():
    perigo = Perigo(
        id=int(row["id"]),
        perigo=row["perigo"],
        consequencias=row["consequencias"],
        salvaguardas=row["salvaguardas"]
    )
    db.merge(perigo)

# =========================
# IMPORTAR EPIs
# =========================
df_epis = pd.read_excel("epis_apr_modelo_validado.xlsx")

for _, row in df_epis.iterrows():
    epi = Epi(
        id=int(row["id"]),
        nome=row["epi"],
        descricao=row["descricao"],
        normas=row["normas"]
    )
    db.merge(epi)

# =========================
# IMPORTAR ATIVIDADES E PASSOS
# =========================
df_passos = pd.read_excel("atividades_passos_apr_modelo_validado.xlsx")

for _, row in df_passos.iterrows():
    atividade = Atividade(
        id=int(row["atividade_id"]),
        nome=row["atividade"],
        local=row["local"],
        funcao=row["funcao"]
    )
    db.merge(atividade)

    passo = Passo(
        atividade_id=int(row["atividade_id"]),
        ordem=int(row["ordem_passo"]),
        descricao=row["descricao_passo"],
        perigos=row["perigos"],
        riscos=row["riscos"],
        medidas_controle=row["medidas_controle"],
        epis=row["epis"],
        normas=row["normas"]
    )
    db.add(passo)

db.commit()
db.close()

print("✅ Importação concluída com sucesso")
