from __future__ import annotations

from typing import Any, Dict, List, Union
import json
import html

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


JsonLike = Union[Dict[str, Any], List[Any]]


def _to_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (int, float, bool)):
        return str(v)
    if isinstance(v, str):
        return v
    try:
        return json.dumps(v, ensure_ascii=False, indent=2, default=str)
    except Exception:
        return str(v)


def _as_list(v: Any) -> List[Any]:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def _safe_para(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(html.escape(_to_str(text)).replace("\n", "<br/>"), style)


def _make_kv_table(data: Dict[str, Any]) -> Table:
    rows = []
    for k, v in data.items():
        rows.append([html.escape(str(k)), html.escape(_to_str(v)).replace("\n", " ")[:2000]])

    tbl = Table(rows, colWidths=[140, 380])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return tbl


def _is_builder_format(documento: Any) -> bool:
    return isinstance(documento, dict) and isinstance(documento.get("documentos"), list)


def gerar_pdf_apr(documento: Any, caminho_saida: str):
    """
    PDF compatível com:
    A) builder -> {"tipo_documento":..., "documentos":[{"apr":{...},"passos":[...]}]}
    B) formato antigo -> atividades -> {"atividades":[...]} etc.
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
    style_h2 = ParagraphStyle("H2", parent=styles["Heading2"], spaceBefore=10, spaceAfter=6)
    style_h3 = ParagraphStyle("H3", parent=styles["Heading3"], spaceBefore=8, spaceAfter=4)
    style_normal = ParagraphStyle("NormalSmall", parent=styles["Normal"], fontSize=10, leading=13)
    style_mono = ParagraphStyle("Mono", parent=styles["Normal"], fontName="Courier", fontSize=8.5, leading=10.5)

    elementos = []

    # TÍTULO
    elementos.append(Paragraph("ANÁLISE PRELIMINAR DE RISCO (APR)", style_title))
    elementos.append(Spacer(1, 12))

    # ============================
    # FORMATO A: BUILDER
    # ============================
    if _is_builder_format(documento):
        elementos.append(Paragraph("Documentos", style_h2))
        elementos.append(Spacer(1, 6))

        docs = documento.get("documentos", [])
        for idx, d in enumerate(docs, start=1):
            if not isinstance(d, dict):
                continue

            apr = d.get("apr", {})
            passos = d.get("passos", [])

            if not isinstance(apr, dict):
                apr = {}
            if not isinstance(passos, list):
                passos = []

            titulo = apr.get("atividade") or f"APR {idx}"
            atividade_id = apr.get("atividade_id") or idx

            elementos.append(Paragraph(html.escape(str(titulo)), style_h3))
            elementos.append(_safe_para(f"ID: {atividade_id}", style_normal))
            elementos.append(Spacer(1, 6))

            # dados da APR (apr dict)
            dados_apr = {}
            for k in ["local", "funcao"]:
                if apr.get(k) is not None:
                    dados_apr[k] = apr.get(k)

            normas_base = apr.get("normas_base")
            if normas_base:
                dados_apr["normas_base"] = normas_base

            if dados_apr:
                elementos.append(_make_kv_table(dados_apr))
                elementos.append(Spacer(1, 8))

            if not passos:
                elementos.append(_safe_para("⚠️ Sem passos cadastrados nesta APR.", style_normal))
                elementos.append(Spacer(1, 10))
                continue

            for p in passos:
                if not isinstance(p, dict):
                    continue

                ordem = p.get("ordem", "")
                desc = p.get("descricao", "")

                elementos.append(_safe_para(f"Passo {ordem}", style_normal))
                elementos.append(_safe_para(desc, style_normal))

                detalhes = []

                perigos = p.get("perigos", [])
                epis = p.get("epis", [])

                if perigos:
                    detalhes.append(("Perigos", ", ".join([_to_str(x) for x in _as_list(perigos)])))
                if epis:
                    detalhes.append(("EPIs", ", ".join([_to_str(x) for x in _as_list(epis)])))

                if p.get("riscos"):
                    detalhes.append(("Riscos", _to_str(p.get("riscos"))))
                if p.get("medidas_controle"):
                    detalhes.append(("Medidas de controle", _to_str(p.get("medidas_controle"))))
                if p.get("normas"):
                    detalhes.append(("Normas", _to_str(p.get("normas"))))

                if detalhes:
                    tbl = Table([[k, v] for k, v in detalhes], colWidths=[120, 400])
                    tbl.setStyle(
                        TableStyle(
                            [
                                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                                ("FONTSIZE", (0, 0), (-1, -1), 9),
                                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                                ("TOPPADDING", (0, 0), (-1, -1), 4),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                            ]
                        )
                    )
                    elementos.append(Spacer(1, 4))
                    elementos.append(tbl)

                elementos.append(Spacer(1, 10))

            if idx < len(docs):
                elementos.append(Spacer(1, 10))

        doc.build(elementos)
        return

    # ============================
    # FORMATO B: FALLBACK antigo
    # ============================
    elementos.append(Paragraph("Conteúdo (fallback JSON)", style_h2))
    elementos.append(Spacer(1, 8))

    texto = _to_str(documento)
    for linha in texto.split("\n"):
        elementos.append(_safe_para(linha, style_mono))

    doc.build(elementos)
