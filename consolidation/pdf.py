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
    PageBreak,
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
    # lista/dict/objetos -> json legível
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


def _get_atividades(documento: Any) -> List[Dict[str, Any]]:
    """
    Aceita:
    - documento dict com chave "atividades"
    - documento dict já sendo atividades (mapeado por id)
    - documento list de atividades
    Retorna lista de dicts.
    """
    if documento is None:
        return []

    # caso 1: dict com "atividades"
    if isinstance(documento, dict) and "atividades" in documento:
        return [a for a in _as_list(documento.get("atividades")) if isinstance(a, dict)]

    # caso 2: list direto
    if isinstance(documento, list):
        return [a for a in documento if isinstance(a, dict)]

    # caso 3: dict mapeado por id -> values
    if isinstance(documento, dict):
        vals = list(documento.values())
        if vals and all(isinstance(x, dict) for x in vals):
            return vals

        # último fallback: tenta achar algo que pareça atividade
        # (ex.: {"data": [...]} )
        for v in documento.values():
            if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
                return v

    return []


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


def gerar_pdf_apr(documento: Any, caminho_saida: str):
    """
    Gerador de PDF FINAL (bonito e robusto).

    - Não assume formato rígido.
    - Nunca chama .keys() em listas.
    - Tenta renderizar uma APR em seções (Atividades -> Passos).
    - Se não conseguir estruturar, faz fallback para JSON.
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
    style_h2 = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        spaceBefore=10,
        spaceAfter=6,
    )
    style_h3 = ParagraphStyle(
        "H3",
        parent=styles["Heading3"],
        spaceBefore=8,
        spaceAfter=4,
    )
    style_normal = ParagraphStyle(
        "NormalSmall",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
    )
    style_mono = ParagraphStyle(
        "Mono",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8.5,
        leading=10.5,
    )

    elementos = []

    # TÍTULO
    elementos.append(Paragraph("ANÁLISE PRELIMINAR DE RISCO (APR)", style_title))
    elementos.append(Spacer(1, 12))

    # METADADOS (se existir)
    if isinstance(documento, dict):
        meta_keys = ["titulo", "empresa", "obra", "local", "data", "responsavel", "setor"]
        meta = {k: documento.get(k) for k in meta_keys if k in documento and documento.get(k) is not None}
        if meta:
            elementos.append(Paragraph("Dados gerais", style_h2))
            elementos.append(_make_kv_table(meta))
            elementos.append(Spacer(1, 10))

    # ATIVIDADES
    atividades = _get_atividades(documento)

    if atividades:
        elementos.append(Paragraph("Atividades", style_h2))
        elementos.append(Spacer(1, 6))

        for idx, atv in enumerate(atividades, start=1):
            nome = atv.get("atividade") or atv.get("nome") or atv.get("titulo") or f"Atividade {idx}"
            atividade_id = atv.get("atividade_id") or atv.get("id") or f"{idx}"

            elementos.append(Paragraph(f"{html.escape(str(nome))}", style_h3))
            elementos.append(_safe_para(f"ID: {atividade_id}", style_normal))
            elementos.append(Spacer(1, 6))

            passos = atv.get("passos", [])
            if not isinstance(passos, list):
                passos = []

            if not passos:
                elementos.append(_safe_para("⚠️ Sem passos cadastrados nesta atividade.", style_normal))
                elementos.append(Spacer(1, 10))
                continue

            # Render dos passos
            for p in passos:
                if not isinstance(p, dict):
                    continue

                ordem = p.get("ordem", "")
                desc = p.get("descricao", "")

                elementos.append(_safe_para(f"Passo {ordem}", style_normal))
                elementos.append(_safe_para(desc, style_normal))

                # Bloco técnico (perigos/epis/riscos/medidas/normas)
                detalhes = []

                # Perigos e EPIs podem vir como IDs ou textos
                perigos = p.get("perigos", [])
                epis = p.get("epis", [])

                if perigos:
                    detalhes.append(("Perigos", ", ".join([_to_str(x) for x in _as_list(perigos)])))
                if epis:
                    detalhes.append(("EPIs", ", ".join([_to_str(x) for x in _as_list(epis)])))

                # Campos opcionais
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

            # quebra entre atividades (leve)
            if idx < len(atividades):
                elementos.append(Spacer(1, 6))

        doc.build(elementos)
        return

    # FALLBACK: NÃO ACHOU ESTRUTURA -> imprime JSON
    elementos.append(Paragraph("Conteúdo (fallback JSON)", style_h2))
    elementos.append(Spacer(1, 8))

    texto = _to_str(documento)
    for linha in texto.split("\n"):
        elementos.append(_safe_para(linha, style_mono))

    doc.build(elementos)
