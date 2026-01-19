from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import json
import html


def gerar_pdf_apr(documento: dict, caminho_saida: str):
    """
    GERADOR DE PDF ULTRA-DEFENSIVO

    - Aceita QUALQUER dict
    - Não assume estrutura
    - Não acessa keys específicas
    - Não itera listas internas
    - Nunca lança exceção estrutural
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

    # ==========================
    # TÍTULO
    # ==========================
    elementos.append(
        Paragraph("ANÁLISE PRELIMINAR DE RISCO (APR)", style_title)
    )
    elementos.append(Spacer(1, 20))

    # ==========================
    # CONTEÚDO COMPLETO (RAW)
    # ==========================
    try:
        texto = json.dumps(
            documento,
            ensure_ascii=False,
            indent=2,
            default=str
        )
    except Exception:
        texto = str(documento)

    for linha in texto.split("\n"):
        linha_segura = html.escape(linha)
        elementos.append(Paragraph(linha_segura, style_normal))

    # ==========================
    # BUILD FINAL
    # ==========================
    doc.build(elementos)
