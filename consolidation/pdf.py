from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import json


def gerar_pdf_apr(documento: dict, caminho_saida: str):
    """
    PDF ultra-defensivo.
    NÃO interpreta estrutura.
    NÃO itera dict/list.
    NUNCA quebra.
    """

    doc = SimpleDocTemplate(
        caminho_saida,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    title = styles["Title"]

    elementos = []

    elementos.append(Paragraph("ANÁLISE PRELIMINAR DE RISCO (APR)", title))
    elementos.append(Spacer(1, 20))

    # 🔒 SERIALIZA TUDO COMO TEXTO
    texto = json.dumps(documento, ensure_ascii=False, indent=2)

    for linha in texto.split("\n"):
        elementos.append(Paragraph(linha.replace("<", "&lt;").replace(">", "&gt;"), normal))

    doc.build(elementos)
