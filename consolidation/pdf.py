from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4


def gerar_pdf_apr(documento: dict, caminho_saida: str):
    """
    Gera PDF técnico da APR a partir de UM documento canônico.
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
    apr = documento["apr"]

    elementos.append(Paragraph("ANÁLISE PRELIMINAR DE RISCO (APR)", style_title))
    elementos.append(Spacer(1, 12))

    elementos.append(Paragraph(f"<b>Atividade:</b> {apr.get('atividade', '')}", style_normal))
    elementos.append(Paragraph(f"<b>Local:</b> {apr.get('local', '')}", style_normal))
    elementos.append(Paragraph(f"<b>Função:</b> {apr.get('funcao', '')}", style_normal))
    elementos.append(Spacer(1, 12))

    elementos.append(Paragraph("<b>Normas Aplicáveis:</b>", style_normal))
    for norma in apr.get("normas_base", []):
        elementos.append(Paragraph(f"- {norma}", style_normal))

    elementos.append(PageBreak())

    # ==========================
    # PASSOS OPERACIONAIS
    # ==========================
    elementos.append(Paragraph("PASSOS OPERACIONAIS", style_h))
    elementos.append(Spacer(1, 12))

    for passo in documento["passos"]:
        elementos.append(Paragraph(f"<b>Passo {passo['ordem']}</b>", style_normal))
        elementos.append(Paragraph(passo["descricao"], style_normal))
        elementos.append(Spacer(1, 6))

        # Perigos
        perigos = ", ".join(p["perigo"] for p in passo.get("perigos", []))
        elementos.append(Paragraph(f"<b>Perigos:</b> {perigos}", style_normal))

        # Riscos
        riscos = ", ".join(passo.get("riscos", []))
        elementos.append(Paragraph(f"<b>Riscos:</b> {riscos}", style_normal))

        # Medidas de controle (DICT POR HIERARQUIA)
        elementos.append(Paragraph("<b>Medidas de Controle:</b>", style_normal))
        for nivel, medidas in passo.get("medidas_controle", {}).items():
            if medidas:
                texto = ", ".join(map(str, medidas))
                elementos.append(
                    Paragraph(f"- {nivel.capitalize()}: {texto}", style_normal)
                )

        # EPIs
        epis = ", ".join(e["epi"] for e in passo.get("epis", []))
        elementos.append(Paragraph(f"<b>EPIs:</b> {epis}", style_normal))

        elementos.append(Spacer(1, 12))

    # ==========================
    # AUDITORIA
    # ==========================
    elementos.append(PageBreak())
    elementos.append(Paragraph("AUDITORIA E RASTREABILIDADE", style_h))
    elementos.append(Spacer(1, 12))

    audit = documento["audit"]
    elementos.append(Paragraph(f"<b>Timestamp:</b> {audit['timestamp']}", style_normal))

    elementos.append(Paragraph("<b>Hash dos arquivos de origem:</b>", style_normal))
    for item in audit.get("hashes_origem", []):
        elementos.append(
            Paragraph(f"- {item['arquivo']}: {item['hash']}", style_normal)
        )

    doc.build(elementos)
