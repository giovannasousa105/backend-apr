from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import json
import html
from typing import Any


def gerar_pdf_apr(documento: Any, caminho_saida: str):
    """
    Gerador de PDF FINAL.
    Aceita SOMENTE estrutura já normalizada.
    Nunca chama .keys() em listas.
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
    style_title = styles["Title"]
    style_normal = styles["Normal"]

    elementos = []

    elementos.append(
        Paragraph("ANÁLISE PRELIMINAR DE RISCO (APR)", style_title)
    )
    elementos.append(Spacer(1, 20))

    texto = json.dumps(
        documento,
        ensure_ascii=False,
        indent=2,
        default=str
    )

    for linha in texto.split("\n"):
        elementos.append(
            Paragraph(html.escape(linha), style_normal)
        )

    doc.build(elementos)
