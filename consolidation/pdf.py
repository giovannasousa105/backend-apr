from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors


def gerar_pdf_apr(documento: dict, caminho_saida: str):
    """
    Gera PDF técnico da APR a partir do documento canônico.
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
    style_normal = styles["Normal"]
    style_title = styles["Title"]
    style_h = styles["Heading2"]

    elementos = []

    # ==========================
    # CAPA
    # ==========================
    apr = documento["documentos"][0]["apr"]

    elementos.append(Paragraph("ANÁLISE PRELIMINAR DE RISCO (APR)", style_title))
    elementos.append(Spacer(1, 12))

    elementos.append(Paragraph(f"<b>Atividade:</b> {apr.get('atividade')}", style_normal))
    elementos.append(Paragraph(f"<b>Local:</b> {apr.get('local')}", style_normal))
    elementos.append(Paragraph(f"<b>Função:</b> {apr.get('funcao')}", style_normal))
    elementos.append(Spacer(1, 12))

    elementos.append(Paragraph("<b>Normas Aplicáveis:</b>", style_normal))
    for norma in apr.get("normas_base", []):
        elementos.append(
            Paragraph(f"- {norma['codigo']}: {norma['titulo']}", style_normal)
        )

    elementos.append(PageBreak())

    # ==========================
    # PASSOS OPERACIONAIS
    # ==========================
    elementos.append(Paragraph("PASSOS OPERACIONAIS", style_h))
    elementos.append(Spacer(1, 12))

    for passo in documento["documentos"][0]["passos"]:
        elementos.append(Paragraph(f"<b>Passo {passo['ordem']}</b>", style_normal))
        elementos.append(Paragraph(passo["descricao"], style_normal))
        elementos.append(Spacer(1, 6))

        # Perigos
        perigos = ", ".join([p["perigo"] for p in passo["perigos"]])
        elementos.append(Paragraph(f"<b>Perigos:</b> {perigos}", style_normal))

        # Riscos
        riscos = ", ".join(passo.get("riscos", []))
        elementos.append(Paragraph(f"<b>Riscos:</b> {riscos}", style_normal))

        # Consequências
        consequencias = ", ".join(passo.get("consequencias", []))
        elementos.append(Paragraph(f"<b>Consequências:</b> {consequencias}", style_normal))

        # Medidas de controle (hierarquia)
        elementos.append(Paragraph("<b>Medidas de Controle:</b>", style_normal))
        for nivel, medidas in passo.get("medidas_controle", {}).items():
            if medidas:
                texto = ", ".join(map(str, medidas))
                elementos.append(
                    Paragraph(f"- <i>{nivel.capitalize()}</i>: {texto}", style_normal)
                )

        elementos.append(Spacer(1, 12))

    # ==========================
    # AUDITORIA
    # ==========================
    elementos.append(PageBreak())
    elementos.append(Paragraph("AUDITORIA E RASTREABILIDADE", style_h))
    elementos.append(Spacer(1, 12))

    audit = documento["documentos"][0]["audit"]
    elementos.append(Paragraph(f"<b>Timestamp:</b> {audit['timestamp']}", style_normal))

    elementos.append(Paragraph("<b>Hash dos arquivos de origem:</b>", style_normal))
    for nome, hash_val in audit["hashes_origem"].items():
        elementos.append(Paragraph(f"- {nome}: {hash_val}", style_normal))

    doc.build(elementos)
