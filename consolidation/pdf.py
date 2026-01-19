raise RuntimeError("PDF.PY DEFINITIVAMENTE EXECUTADO")
print(">>> PDF.PY FOI IMPORTADO <<<")
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import json
import html

def gerar_pdf_apr(documento: dict, caminho_saida: str):
    """
    Recebe QUALQUER dict e nunca quebra.
    """
    print(">>> GERAR_PDF_APR EXECUTADO <<<")

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

    # Título
    elementos.append(Paragraph("ANÁLISE PRELIMINAR DE RISCO (APR)", title))
    elementos.append(Spacer(1, 20))

    # Serializa tudo como texto seguro
    try:
        texto = json.dumps(documento, ensure_ascii=False, indent=2)
    except Exception:
        texto = str(documento)

    for linha in texto.split("\n"):
        linha_segura = html.escape(linha)
        elementos.append(Paragraph(linha_segura, normal))

    doc.build(elementos)
