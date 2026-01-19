from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import json
import html
from typing import Any


def normalizar_documento(dados: Any) -> dict:
    """
    NORMALIZA QUALQUER ENTRADA PARA DICT

    - list      -> {"registros": list}
    - dict      -> dict
    - outros    -> {"valor": str(obj)}

    Garante que o PDF sempre receba um dict
    """
    try:
        if isinstance(dados, dict):
            return dados

        if isinstance(dados, list):
            return {"registros": dados}

        return {"valor": str(dados)}

    except Exception as e:
        return {"erro_normalizacao": str(e)}


def gerar_pdf_apr(documento: Any, caminho_saida: str):
    """
    GERADOR DE PDF ULTRA-ROBUSTO

    ✔ Aceita dict, list, qualquer objeto
    ✔ Nunca assume estrutura
    ✔ Nunca usa .keys()
    ✔ Nunca lança exceção estrutural
    ✔ Ideal para produção (APR, relatórios, auditorias)
    """

    # ==========================
    # NORMALIZA ENTRADA
    # ==========================
    documento = normalizar_documento(documento)

    # ==========================
    # CONFIGURA PDF
    # ==========================
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
    # CONTEÚDO (RAW DEFENSIVO)
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
    # BUILD FINAL (NUNCA QUEBRA)
    # ==========================
    try:
        doc.build(elementos)
    except Exception as e:
        # fallback extremo: PDF mínimo
        elementos_fallback = [
            Paragraph("Erro ao gerar PDF APR", style_title),
            Spacer(1, 12),
            Paragraph(html.escape(str(e)), style_normal),
        ]
        doc.build(elementos_fallback)
