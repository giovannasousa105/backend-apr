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
    Estrutura defensiva (nunca quebra).
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
    apr = documento.get("apr", {})

    elementos.append(Paragraph("ANÁLISE PRELIMINAR DE RISCO (APR)", style_title))
    elementos.append(Spacer(1, 12))

    elementos.append(Paragraph(f"<b>Atividade:</b> {apr.get('atividade','')}", style_normal))
    elementos.append(Paragraph(f"<b>Local:</b> {apr.get('local','')}", style_normal))
    elementos.append(Paragraph(f"<b>Função:</b> {apr.get('funcao','')}", style_normal))
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

    for passo in documento.get("passos", []):
        elementos.append(Paragraph(f"<b>Passo {passo.get('ordem')}</b>", style_normal))
        elementos.append(Paragraph(passo.get("descricao",""), style_normal))
        elementos.append(Spacer(1, 6))

        perigos = ", ".join(p.get("perigo","") for p in passo.get("perigos", []))
        elementos.append(Paragraph(f"<b>Perigos:</b> {perigos}", style_normal))

        riscos = ", ".join(passo.get("riscos", []))
        elementos.append(Paragraph(f"<b>Riscos:</b> {riscos}", style_normal))

        # 🔑 MEDIDAS — aceita dict OU list
        elementos.append(Paragraph("<b>Medidas de Controle:</b>", style_normal))
        mc = passo.get("medidas_controle", {})

        if isinstance(mc, dict):
            for nivel, medidas in mc.items():
                if medidas:
                    elementos.append(
                        Paragraph(f"- {nivel.capitalize()}: {', '.join(map(str, medidas))}", style_normal)
                    )
        elif isinstance(mc, list):
            elementos.append(
                Paragraph("- " + ", ".join(map(str, mc)), style_normal)
            )

        epis = ", ".join(e.get("epi","") for e in passo.get("epis", []))
        elementos.append(Paragraph(f"<b>EPIs:</b> {epis}", style_normal))

        elementos.append(Spacer(1, 12))

    # ==========================
    # AUDITORIA
    # ==========================
    elementos.append(PageBreak())
    elementos.append(Paragraph("AUDITORIA E RASTREABILIDADE", style_h))
    elementos.append(Spacer(1, 12))

    audit = documento.get("audit", {})
    elementos.append(Paragraph(f"<b>Timestamp:</b> {audit.get('timestamp','')}", style_normal))

    elementos.append(Paragraph("<b>Hash dos arquivos de origem:</b>", style_normal))
    hashes = audit.get("hashes_origem", [])

    # 🔑 aceita LIST ou DICT
    if isinstance(hashes, dict):
        for nome, valor in hashes.items():
            elementos.append(Paragraph(f"- {nome}: {valor}", style_normal))
    elif isinstance(hashes, list):
        for item in hashes:
            elementos.append(
                Paragraph(f"- {item.get('arquivo','')}: {item.get('hash','')}", style_normal)
            )

    doc.build(elementos)
