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
    Função defensiva (nunca quebra com list/dict)
    """

    # 🔒 DEFESA ABSOLUTA
    if "documentos" in documento:
        documento = documento["documentos"][0]

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
    h = styles["Heading2"]

    elementos = []

    # ======================
    # CAPA
    # ======================
    apr = documento.get("apr", {})

    elementos.append(Paragraph("ANÁLISE PRELIMINAR DE RISCO (APR)", title))
    elementos.append(Spacer(1, 12))

    elementos.append(Paragraph(f"<b>Atividade:</b> {apr.get('atividade','-')}", normal))
    elementos.append(Paragraph(f"<b>Local:</b> {apr.get('local','-')}", normal))
    elementos.append(Paragraph(f"<b>Função:</b> {apr.get('funcao','-')}", normal))
    elementos.append(Spacer(1, 12))

    elementos.append(Paragraph("<b>Normas Aplicáveis:</b>", normal))
    for norma in apr.get("normas_base", []):
        if isinstance(norma, dict):
            elementos.append(Paragraph(f"- {norma.get('codigo','')}: {norma.get('titulo','')}", normal))
        else:
            elementos.append(Paragraph(f"- {norma}", normal))

    elementos.append(PageBreak())

    # ======================
    # PASSOS
    # ======================
    elementos.append(Paragraph("PASSOS OPERACIONAIS", h))
    elementos.append(Spacer(1, 12))

    for passo in documento.get("passos", []):
        elementos.append(Paragraph(f"<b>Passo {passo.get('ordem','')}</b>", normal))
        elementos.append(Paragraph(passo.get("descricao",""), normal))
        elementos.append(Spacer(1, 6))

        perigos = ", ".join(p.get("perigo","") for p in passo.get("perigos", []))
        elementos.append(Paragraph(f"<b>Perigos:</b> {perigos}", normal))

        riscos = ", ".join(passo.get("riscos", []))
        elementos.append(Paragraph(f"<b>Riscos:</b> {riscos}", normal))

        # 🔥 MEDIDAS – aceita LIST ou DICT
        mc = passo.get("medidas_controle", [])
        if isinstance(mc, dict):
            texto = "; ".join(
                f"{k}: {', '.join(v)}" if isinstance(v, list) else f"{k}: {v}"
                for k, v in mc.items()
            )
        else:
            texto = ", ".join(mc)

        elementos.append(Paragraph(f"<b>Medidas de Controle:</b> {texto}", normal))

        epis = ", ".join(e.get("epi","") for e in passo.get("epis", []))
        elementos.append(Paragraph(f"<b>EPIs:</b> {epis}", normal))

        elementos.append(Spacer(1, 12))

    # ======================
    # AUDITORIA
    # ======================
    elementos.append(PageBreak())
    elementos.append(Paragraph("AUDITORIA E RASTREABILIDADE", h))
    elementos.append(Spacer(1, 12))

    audit = documento.get("audit", {})
    elementos.append(Paragraph(f"<b>Timestamp:</b> {audit.get('timestamp','')}", normal))

    elementos.append(Paragraph("<b>Hash dos arquivos de origem:</b>", normal))
    hashes = audit.get("hashes_origem", {})
    if isinstance(hashes, dict):
        for nome, valor in hashes.items():
            elementos.append(Paragraph(f"- {nome}: {valor}", normal))

    doc.build(elementos)
