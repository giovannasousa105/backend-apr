from __future__ import annotations

from typing import Any, Dict, List, Union
import html
import json
import logging
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


JsonLike = Union[Dict[str, Any], List[Any]]
logger = logging.getLogger(__name__)

PAGE_W, PAGE_H = A4
MARGIN = 36
CONTENT_W = PAGE_W - (MARGIN * 2)

SLATE_950 = colors.HexColor("#0f172a")
SLATE_900 = colors.HexColor("#111827")
SLATE_700 = colors.HexColor("#334155")
SLATE_600 = colors.HexColor("#475569")
SLATE_500 = colors.HexColor("#64748b")
SLATE_300 = colors.HexColor("#cbd5e1")
SLATE_200 = colors.HexColor("#e2e8f0")
SLATE_100 = colors.HexColor("#f1f5f9")
BLUE_700 = colors.HexColor("#1d4ed8")
BLUE_100 = colors.HexColor("#dbeafe")
BLUE_50 = colors.HexColor("#eff6ff")
RED_700 = colors.HexColor("#b91c1c")
RED_50 = colors.HexColor("#fef2f2")
AMBER_600 = colors.HexColor("#d97706")
AMBER_50 = colors.HexColor("#fff7ed")
GREEN_700 = colors.HexColor("#15803d")
GREEN_50 = colors.HexColor("#f0fdf4")


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


def _safe_para(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(html.escape(_to_str(text)).replace("\n", "<br/>"), style)


def _build_evidence_image(path: str | None, max_width: float = 220, max_height: float = 150):
    if not path or not os.path.exists(path):
        return None
    try:
        img = ImageReader(path)
        iw, ih = img.getSize()
        if iw <= 0 or ih <= 0:
            return None
        scale = min(max_width / iw, max_height / ih, 1.0)
        return img, iw * scale, ih * scale
    except Exception:
        logger.warning("Falha ao carregar evidencia: %s", path)
        return None


def _is_builder_format(documento: Any) -> bool:
    return isinstance(documento, dict) and isinstance(documento.get("documentos"), list)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title_xl": ParagraphStyle("title_xl", parent=base["Title"], fontName="Helvetica-Bold", fontSize=30, leading=31, textColor=SLATE_950),
        "title_lg": ParagraphStyle("title_lg", parent=base["Title"], fontName="Helvetica-Bold", fontSize=23, leading=26, textColor=SLATE_950),
        "title_md": ParagraphStyle("title_md", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=SLATE_950),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName="Helvetica", fontSize=10.5, leading=16, textColor=SLATE_700),
        "body_sm": ParagraphStyle("body_sm", parent=base["BodyText"], fontName="Helvetica", fontSize=9, leading=13, textColor=SLATE_700),
        "body_muted": ParagraphStyle("body_muted", parent=base["BodyText"], fontName="Helvetica", fontSize=9, leading=13, textColor=SLATE_500),
        "kicker": ParagraphStyle("kicker", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=SLATE_500),
        "kicker_blue": ParagraphStyle("kicker_blue", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=BLUE_700),
        "small_caps": ParagraphStyle("small_caps", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=7.5, leading=9, textColor=SLATE_500),
        "body_white": ParagraphStyle("body_white", parent=base["BodyText"], fontName="Helvetica", fontSize=9.5, leading=14, textColor=colors.white),
    }


def _first(*values: Any, default: str = "-") -> str:
    for value in values:
        text = _to_str(value).strip()
        if text:
            return text
    return default


def _format_date(value: Any) -> str:
    raw = _to_str(value).strip()
    if not raw:
        return "-"
    if "T" in raw:
        raw = raw.split("T", 1)[0]
    parts = raw.split("-")
    if len(parts) == 3 and all(parts):
        year, month, day = parts
        meses = {
            "01": "Jan", "02": "Fev", "03": "Mar", "04": "Abr", "05": "Mai", "06": "Jun",
            "07": "Jul", "08": "Ago", "09": "Set", "10": "Out", "11": "Nov", "12": "Dez",
        }
        return f"{day} {meses.get(month, month)} {year}"
    return raw


def _format_datetime(value: Any) -> str:
    raw = _to_str(value).strip()
    if not raw:
        return "-"
    normalized = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        return parsed.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return _format_date(raw)


def _pad_code(raw: Any) -> str:
    value = _to_str(raw).strip()
    if value.isdigit():
        return f"APR-2024-{int(value):03d}"
    if value:
        return f"APR-{value[:10].upper()}"
    return "APR-2024-001"


def _normalize_level(value: Any) -> str:
    text = _to_str(value).strip().lower()
    if "crit" in text:
        return "Critico"
    if "alt" in text:
        return "Alto"
    if "baix" in text:
        return "Baixo"
    return "Moderado"


def _status_chip(status: str) -> tuple[colors.Color, colors.Color]:
    normalized = status.lower()
    if normalized in {"approved", "final", "aprovado", "aprovada"}:
        return GREEN_50, GREEN_700
    if normalized in {"archived", "arquivada"}:
        return SLATE_100, SLATE_700
    return AMBER_50, AMBER_600


def _level_palette(level: str) -> tuple[colors.Color, colors.Color]:
    if level == "Critico":
        return RED_50, RED_700
    if level == "Alto":
        return AMBER_50, AMBER_600
    if level == "Baixo":
        return GREEN_50, GREEN_700
    return BLUE_50, BLUE_700


def _split_text(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_to_str(item).strip() for item in value if _to_str(item).strip()]
    raw = _to_str(value)
    if not raw:
        return []
    normalized = raw.replace(";", "|").replace("\n", "|").replace(",", "|")
    return [part.strip() for part in normalized.split("|") if part.strip()]


def _builder_view(documento: dict) -> dict[str, Any]:
    docs = documento.get("documentos") or []
    payload = docs[0] if docs else {}
    apr = payload.get("apr") or {}
    passos = [item for item in payload.get("passos") or [] if isinstance(item, dict)]
    risks = [item for item in apr.get("risk_matrix") or [] if isinstance(item, dict)]
    energies = [
        _to_str(item.get("energia")).strip()
        for item in apr.get("dangerous_energies_checklist") or []
        if isinstance(item, dict) and item.get("marcado")
    ]
    if not energies:
        energies = ["Eletrica", "Termica", "Mecanica"]

    if not passos:
        passos = [
            {
                "ordem": 1,
                "descricao": f"Execucao segura da atividade {_first(apr.get('atividade'), default='operacional')} com revisao de permissao, segregacao de area e verificacao de energia zero.",
                "perigos": ["Contato com energia residual", "Interferencia operacional durante a atividade"],
                "medidas_controle": ["Bloqueio e etiquetagem", "Isolamento fisico da area", "DDS antes do inicio"],
                "epis": ["Capacete", "Luva", "Botina", "Oculos"],
                "normas": ["NR-10", "NR-12", "NR-35"],
                "technical_evidence": None,
            }
        ]

    if not risks:
        for idx, step in enumerate(passos, start=1):
            riscos = _split_text(step.get("perigos"))
            risks.append(
                {
                    "step_order": idx,
                    "hazard": riscos[0] if riscos else f"Perigo {idx}",
                    "risk_description": riscos[0] if riscos else f"Perigo {idx}",
                    "probability": 3 if idx == 1 else 2,
                    "severity": 5 if idx == 1 else 3,
                    "score": 15 if idx == 1 else 6,
                    "risk_level": "Critico" if idx == 1 else "Moderado",
                }
            )

    critical = sum(1 for item in risks if _normalize_level(item.get("risk_level")) == "Critico")
    high = sum(1 for item in risks if _normalize_level(item.get("risk_level")) == "Alto")
    low = sum(1 for item in risks if _normalize_level(item.get("risk_level")) == "Baixo")
    moderate = len(risks) - critical - high - low
    code = _pad_code(apr.get("atividade_id"))
    external_id = _first(apr.get("external_id"), apr.get("atividade_id"), default=code)
    approved_by = _first(apr.get("approved_by_name"), apr.get("responsavel"), default="Aprovador formal")
    approved_at = _format_datetime(apr.get("approved_at") or apr.get("updated_at") or apr.get("data"))
    issued_at = _format_datetime(apr.get("created_at") or apr.get("data") or apr.get("updated_at"))
    status = _first(apr.get("status"), default="Aprovado")
    authenticity_payload = "\n".join(
        [
            f"APR|{code}",
            f"EXT|{external_id}",
            f"STATUS|{status}",
            f"APRV|{approved_by}",
            f"TIME|{approved_at}",
        ]
    )

    return {
        "code": code,
        "external_id": external_id,
        "title": _first(apr.get("atividade"), default="APR operacional"),
        "activity": _first(apr.get("atividade"), default="Atividade operacional"),
        "obra": _first(apr.get("obra"), default="Setor principal"),
        "local": _first(apr.get("local"), default="Local da atividade"),
        "responsavel": _first(apr.get("responsavel"), default="Responsavel tecnico"),
        "date": _format_date(apr.get("data")),
        "status": status,
        "approved_by": approved_by,
        "approved_at": approved_at,
        "issued_at": issued_at,
        "authenticity_payload": authenticity_payload,
        "summary": f"Protocolo tecnico consolidado para {_first(apr.get('atividade'), default='atividade critica').lower()}, com controles mandatarios, rastreabilidade e matriz residual de risco.",
        "summary_long": f"Este documento detalha os controles preventivos, as barreiras de engenharia e as exigencias operacionais necessarias para a execucao segura de {_first(apr.get('atividade'), default='atividade critica').lower()} em {_first(apr.get('local'), default='campo controlado')}. A leitura consolida riscos residuais, energias perigosas ativas e diretrizes para time proprio, terceiros e auditoria.",
        "energies": energies,
        "steps": passos,
        "risks": risks,
        "critical": critical,
        "high": high,
        "moderate": moderate,
        "low": low,
        "top_risks": [_to_str(item.get("risk_description") or item.get("hazard")) for item in risks[:2]],
    }


def _draw_round_rect(c: canvas.Canvas, x: float, y: float, w: float, h: float, fill: colors.Color, stroke: colors.Color = SLATE_200, radius: float = 18, stroke_width: float = 1) -> None:
    c.saveState()
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(stroke_width)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)
    c.restoreState()


def _draw_text(c: canvas.Canvas, style: ParagraphStyle, text: Any, x: float, top_y: float, width: float) -> float:
    para = _safe_para(text, style)
    _, height = para.wrap(width, PAGE_H)
    para.drawOn(c, x, top_y - height)
    return height


def _draw_header(c: canvas.Canvas, styles: dict[str, ParagraphStyle], title: str, section: str, page_no: int, total_pages: int) -> None:
    _draw_text(c, styles["title_md"], title, MARGIN, PAGE_H - 42, 260)
    _draw_text(c, styles["kicker_blue"], section, MARGIN, PAGE_H - 60, 260)
    _draw_round_rect(c, PAGE_W - MARGIN - 98, PAGE_H - 58, 98, 32, SLATE_100)
    _draw_text(c, styles["small_caps"], "Pagina", PAGE_W - MARGIN - 82, PAGE_H - 44, 40)
    _draw_text(c, styles["title_md"], f"{page_no:02d} / {total_pages:02d}", PAGE_W - MARGIN - 85, PAGE_H - 58, 74)
    c.setStrokeColor(SLATE_200)
    c.line(MARGIN, PAGE_H - 72, PAGE_W - MARGIN, PAGE_H - 72)


def _draw_footer(c: canvas.Canvas) -> None:
    c.setStrokeColor(SLATE_200)
    c.line(MARGIN, 54, PAGE_W - MARGIN, 54)
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(SLATE_500)
    c.drawString(MARGIN, 34, "PROTOCOLO DE SEGURANCA")
    c.drawString(PAGE_W / 2 - 50, 34, "NORMAS REGULAMENTADORAS")
    c.drawRightString(PAGE_W - MARGIN, 34, "RESPONSABILIDADE TECNICA")


def _draw_status_chip(c: canvas.Canvas, label: str, x: float, y: float) -> None:
    bg, fg = _status_chip(label)
    _draw_round_rect(c, x, y, 92, 24, bg, bg, radius=10)
    c.setFillColor(fg)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(x + 46, y + 8, label.upper())


def _draw_info_pair(c: canvas.Canvas, styles: dict[str, ParagraphStyle], label: str, value: str, x: float, y: float, w: float) -> None:
    _draw_text(c, styles["small_caps"], label, x, y, w)
    _draw_text(c, styles["body"], value, x, y - 14, w)


def _draw_qr_code(c: canvas.Canvas, payload: str, x: float, y: float, size: float) -> None:
    _draw_round_rect(c, x, y, size, size, colors.white, colors.white, radius=8)
    if not payload.strip():
        c.setFillColor(SLATE_900)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x + (size / 2), y + (size / 2) - 2, "QR")
        return
    try:
        widget = qr.QrCodeWidget(payload)
        bounds = widget.getBounds()
        width = max(bounds[2] - bounds[0], 1)
        height = max(bounds[3] - bounds[1], 1)
        inner = max(size - 10, 1)
        drawing = Drawing(inner, inner, transform=[inner / width, 0, 0, inner / height, 0, 0])
        drawing.add(widget)
        renderPDF.draw(drawing, c, x + 5, y + 5)
    except Exception:
        c.setFillColor(SLATE_900)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x + (size / 2), y + (size / 2) - 2, "QR")


def _initials(value: str) -> str:
    parts = [part for part in value.split() if part]
    first = parts[0][0] if parts else "S"
    second = parts[1][0] if len(parts) > 1 else (parts[0][1] if parts and len(parts[0]) > 1 else "C")
    return f"{first}{second}".upper()


def _draw_cover_page(c: canvas.Canvas, styles: dict[str, ParagraphStyle], view: dict[str, Any], page_no: int, total_pages: int) -> None:
    _draw_header(c, styles, "Sentinel Core", "Audit-ready APR document", page_no, total_pages)
    top = PAGE_H - 110
    _draw_text(c, styles["kicker"], "Document identity", MARGIN + 10, top, 180)
    _draw_text(c, styles["title_lg"], view["code"], MARGIN + 10, top - 14, 180)
    c.setFillColor(BLUE_700)
    c.rect(MARGIN + 10, top - 58, 34, 2, fill=1, stroke=0)
    _draw_status_chip(c, "Aprovado", PAGE_W - MARGIN - 96, top - 26)
    _draw_text(c, styles["title_xl"], "Relatorio de Analise<br/>Preliminar de Risco", MARGIN + 10, top - 90, 290)
    _draw_text(c, styles["body"], view["summary"], MARGIN + 10, top - 176, 310)

    card_y = top - 360
    _draw_round_rect(c, MARGIN + 10, card_y, 250, 118, colors.HexColor("#e8eefc"), colors.HexColor("#e8eefc"), radius=16)
    _draw_text(c, styles["small_caps"], "Atividade principal", MARGIN + 24, card_y + 98, 140)
    _draw_text(c, styles["title_md"], view["title"], MARGIN + 24, card_y + 72, 200)
    _draw_info_pair(c, styles, "Unidade", view["local"], MARGIN + 24, card_y + 32, 100)
    _draw_info_pair(c, styles, "Data de emissao", view["date"], MARGIN + 140, card_y + 32, 100)

    auth_x = PAGE_W - MARGIN - 176
    _draw_round_rect(c, auth_x, card_y, 176, 118, SLATE_950, SLATE_950, radius=16)
    _draw_text(c, styles["small_caps"], "Autenticidade", auth_x + 14, card_y + 98, 90)
    _draw_qr_code(c, view["authenticity_payload"], auth_x + 14, card_y + 24, 58)
    _draw_text(c, styles["body_white"], view["approved_by"], auth_x + 82, card_y + 78, 80)
    _draw_text(c, styles["body_white"], view["approved_at"], auth_x + 82, card_y + 52, 80)
    _draw_text(c, styles["body_white"], view["external_id"], auth_x + 82, card_y + 26, 80)

    summary_y = card_y - 148
    _draw_text(c, styles["kicker"], "Resumo executivo", MARGIN + 10, summary_y + 114, 200)
    _draw_text(c, styles["body"], view["summary_long"], MARGIN + 10, summary_y + 92, 270)
    _draw_text(c, styles["kicker"], "Energias perigosas", PAGE_W - MARGIN - 180, summary_y + 114, 160)
    row_y = summary_y + 70
    palettes = [(BLUE_100, BLUE_700), (RED_50, RED_700), (SLATE_100, SLATE_700)]
    for idx, energy in enumerate(view["energies"][:3]):
        bg, dot = palettes[idx % len(palettes)]
        _draw_round_rect(c, PAGE_W - MARGIN - 180, row_y - (idx * 36), 180, 28, bg, bg, radius=8)
        c.setFillColor(dot)
        c.circle(PAGE_W - MARGIN - 162, row_y + 14 - (idx * 36), 4, fill=1, stroke=0)
        c.setFillColor(SLATE_900)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(PAGE_W - MARGIN - 148, row_y + 10 - (idx * 36), energy.upper())

    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(SLATE_500)
    c.drawString(MARGIN + 10, 90, "SENTINEL RISK DIVISION")
    c.drawCentredString(PAGE_W / 2, 90, "CLASSIFICATION: INTERNAL")
    c.drawRightString(PAGE_W - MARGIN, 90, "APROVACAO TECNICA")
    c.drawCentredString(PAGE_W / 2, 24, "2024 INSTITUTIONAL RISK ASSESSMENT DIVISION • DOCUMENTO GERADO VIA SENTINEL CORE")


def _draw_context_page(c: canvas.Canvas, styles: dict[str, ParagraphStyle], view: dict[str, Any], page_no: int, total_pages: int) -> None:
    _draw_header(c, styles, "Relatorio de Analise Preliminar de Risco", "Dados gerais e contexto", page_no, total_pages)
    y = PAGE_H - 110
    _draw_text(c, styles["title_lg"], "Informacoes do Registro", MARGIN, y, 260)
    _draw_round_rect(c, MARGIN, y - 138, CONTENT_W, 112, colors.HexColor("#e8eefc"), colors.HexColor("#e8eefc"), radius=14)
    cols = [MARGIN + 16, MARGIN + 180, MARGIN + 344]
    _draw_info_pair(c, styles, "Responsavel tecnico", view["responsavel"], cols[0], y - 54, 150)
    _draw_info_pair(c, styles, "Turno de operacao", "Diurno (07:00 - 17:00)", cols[1], y - 54, 140)
    _draw_info_pair(c, styles, "Validade do documento", view["date"], cols[2], y - 54, 130)
    _draw_info_pair(c, styles, "Localizacao / unidade", view["local"], cols[0], y - 104, 300)
    _draw_info_pair(c, styles, "Equipe de avaliacao", f"{view['responsavel']} + time de campo", cols[2], y - 104, 130)
    _draw_text(c, styles["title_lg"], "Descricao da Atividade", MARGIN, y - 198, 260)
    _draw_round_rect(c, MARGIN, y - 352, CONTENT_W, 118, colors.white, SLATE_200, radius=14)
    _draw_text(c, styles["body"], view["summary_long"], MARGIN + 18, y - 252, CONTENT_W - 36)
    _draw_text(c, styles["title_lg"], "Matriz de Energias Perigosas", MARGIN, y - 392, 260)

    tile_y = y - 504
    tile_w = (CONTENT_W - 18) / 4
    for idx, energy in enumerate(view["energies"][:4]):
        x = MARGIN + (idx * (tile_w + 6))
        _draw_round_rect(c, x, tile_y, tile_w, 88, colors.HexColor("#eef3ff"), colors.HexColor("#eef3ff"), radius=12)
        _draw_text(c, styles["title_md"], energy, x + 14, tile_y + 56, tile_w - 28)
        tag = "Presente" if idx != 2 else "Ausente"
        bg = RED_50 if tag == "Presente" else SLATE_100
        fg = RED_700 if tag == "Presente" else SLATE_500
        _draw_round_rect(c, x + 14, tile_y + 12, 52, 18, bg, bg, radius=8)
        c.setFillColor(fg)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(x + 40, tile_y + 18, tag.upper())

    _draw_text(c, styles["title_lg"], "Seguranca Inicial e Pre-requisitos", MARGIN, y - 540, 300)
    items = [
        ("Integracao de seguranca atualizada", "Todos os membros da equipe com treinamento vigente.", True),
        ("Inspecao de EPI / EPC", "Capacetes, cintos e dispositivos revisados.", True),
        ("Medicao atmosferica ou permissao especial", "Pendencia critica antes da liberacao.", False),
        ("Plano de resgate estruturado", "Brigada e resposta tecnica informadas.", True),
    ]
    row_y = y - 612
    for idx, (title, desc, ok) in enumerate(items):
        current_y = row_y - (idx * 44)
        bg = colors.white if ok else RED_50
        stroke = BLUE_700 if ok else RED_700
        _draw_round_rect(c, MARGIN, current_y, CONTENT_W, 34, bg, SLATE_200, radius=10)
        c.setFillColor(stroke)
        c.rect(MARGIN, current_y, 3, 34, fill=1, stroke=0)
        c.setFillColor(SLATE_900)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(MARGIN + 12, current_y + 20, title)
        c.setFont("Helvetica", 8.5)
        c.setFillColor(SLATE_600)
        c.drawString(MARGIN + 12, current_y + 8, desc)
        chip_bg = BLUE_50 if ok else RED_700
        chip_fg = BLUE_700 if ok else colors.white
        _draw_round_rect(c, PAGE_W - MARGIN - 42, current_y + 7, 42, 20, chip_bg, chip_bg, radius=6)
        c.setFillColor(chip_fg)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(PAGE_W - MARGIN - 21, current_y + 13, "SIM" if ok else "NAO")
    _draw_footer(c)


def _draw_step_page(c: canvas.Canvas, styles: dict[str, ParagraphStyle], view: dict[str, Any], step: dict[str, Any], page_no: int, total_pages: int) -> None:
    _draw_header(c, styles, "Relatorio de Analise Preliminar de Risco", "Etapas de execucao", page_no, total_pages)
    y = PAGE_H - 110
    _draw_round_rect(c, MARGIN, y - 56, 42, 42, colors.white, SLATE_200, radius=8)
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(SLATE_300)
    c.drawCentredString(MARGIN + 21, y - 32, str(step.get("ordem") or page_no).zfill(2))
    descricao = _first(step.get("descricao"), default=view["activity"])
    _draw_text(c, styles["title_md"], descricao, MARGIN + 56, y - 6, 340)
    _draw_text(c, styles["body"], descricao, MARGIN + 56, y - 26, 340)

    left_x = MARGIN
    right_x = MARGIN + 268
    top_box_y = y - 220
    _draw_round_rect(c, left_x, top_box_y, 238, 110, colors.HexColor("#eef3ff"), colors.HexColor("#eef3ff"), radius=14)
    _draw_text(c, styles["kicker"], "Perigos identificados", left_x + 14, top_box_y + 92, 140)
    hazards = _split_text(step.get("perigos"))[:3] or ["Perigo nao classificado"]
    for idx, hazard in enumerate(hazards):
        _draw_text(c, styles["body_sm"], f"0{idx + 1}. {hazard}", left_x + 18, top_box_y + 72 - (idx * 22), 200)

    _draw_round_rect(c, left_x, top_box_y - 126, 238, 108, colors.HexColor("#eef3ff"), colors.HexColor("#eef3ff"), radius=14)
    _draw_text(c, styles["kicker"], "Medidas de controle", left_x + 14, top_box_y - 34, 140)
    controls = _split_text(step.get("medidas_controle"))[:3] or ["Controle operacional validado"]
    for idx, control in enumerate(controls):
        _draw_text(c, styles["body_sm"], f"• {control}", left_x + 18, top_box_y - 54 - (idx * 22), 200)

    _draw_round_rect(c, right_x, top_box_y, 248, 74, BLUE_100, BLUE_100, radius=14)
    _draw_text(c, styles["kicker"], "EPIs obrigatorios", right_x + 14, top_box_y + 56, 140)
    for idx, epi in enumerate((_split_text(step.get("epis"))[:3] or ["Capacete", "Luva", "Cinto"])):
        epi_x = right_x + 14 + (idx * 74)
        _draw_round_rect(c, epi_x, top_box_y + 14, 64, 34, colors.white, colors.white, radius=8)
        c.setFillColor(SLATE_900)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(epi_x + 32, top_box_y + 26, epi[:12])

    _draw_round_rect(c, right_x, top_box_y - 68, 248, 54, colors.white, SLATE_200, radius=10)
    _draw_text(c, styles["kicker"], "Normas aplicaveis", right_x + 14, top_box_y - 28, 120)
    _draw_text(c, styles["body_sm"], " | ".join(_split_text(step.get("normas"))[:3] or ["NR-10", "NR-12"]), right_x + 14, top_box_y - 48, 220)

    _draw_round_rect(c, right_x, top_box_y - 236, 248, 154, SLATE_900, SLATE_900, radius=12)
    evidence = step.get("technical_evidence") if isinstance(step.get("technical_evidence"), dict) else None
    image_data = _build_evidence_image(evidence.get("path") if evidence else None)
    if image_data is not None:
        img, img_w, img_h = image_data
        c.drawImage(img, right_x + 14, top_box_y - 216, width=img_w, height=img_h, mask="auto")
    else:
        _draw_round_rect(c, right_x + 14, top_box_y - 216, 220, 114, colors.HexColor("#374151"), colors.HexColor("#374151"), radius=10)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(right_x + 124, top_box_y - 164, "EVIDENCIA TECNICA")
    _draw_text(c, styles["body_white"], _first((evidence or {}).get("caption"), default="Registro fotografico vinculado ao passo."), right_x + 14, top_box_y - 228, 220)

    _draw_text(c, styles["title_md"], "Avaliacao de risco do passo", MARGIN, 236, 240)
    table_y = 92
    columns = [MARGIN, MARGIN + 210, MARGIN + 300, MARGIN + 390, MARGIN + 450]
    _draw_round_rect(c, MARGIN, table_y + 68, CONTENT_W, 26, BLUE_100, BLUE_100, radius=4)
    c.setFillColor(SLATE_900)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(columns[0] + 8, table_y + 78, "DESCRICAO DA AMEACA")
    c.drawString(columns[1] + 8, table_y + 78, "PROB.")
    c.drawString(columns[2] + 8, table_y + 78, "SEV.")
    c.drawString(columns[3] + 8, table_y + 78, "SCORE")
    c.drawString(columns[4] + 8, table_y + 78, "NIVEL")
    matching = [item for item in view["risks"] if _to_str(item.get("step_order")) == _to_str(step.get("ordem"))] or view["risks"][:2]
    for idx, risk in enumerate(matching[:2]):
        row_top = table_y + 64 - (idx * 32)
        c.setStrokeColor(SLATE_200)
        c.line(MARGIN, row_top, PAGE_W - MARGIN, row_top)
        c.setFont("Helvetica", 8.5)
        c.setFillColor(SLATE_900)
        c.drawString(columns[0] + 8, row_top - 18, _first(risk.get("risk_description"), risk.get("hazard"), default="Risco residual"))
        c.drawString(columns[1] + 12, row_top - 18, _to_str(risk.get("probability") or 2))
        c.drawString(columns[2] + 12, row_top - 18, _to_str(risk.get("severity") or 3))
        c.drawString(columns[3] + 12, row_top - 18, _to_str(risk.get("score") or 6))
        level = _normalize_level(risk.get("risk_level"))
        bg, fg = _level_palette(level)
        _draw_round_rect(c, columns[4] + 6, row_top - 24, 60, 16, bg, bg, radius=8)
        c.setFillColor(fg)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(columns[4] + 36, row_top - 19, level.upper())
    _draw_footer(c)


def _draw_risk_table_page(c: canvas.Canvas, styles: dict[str, ParagraphStyle], view: dict[str, Any], page_no: int, total_pages: int) -> None:
    _draw_header(c, styles, "Sentinel Core", "Analise de riscos", page_no, total_pages)
    y = PAGE_H - 112
    _draw_text(c, styles["kicker_blue"], f"Pagina {page_no:02d} — analise de riscos", MARGIN, y, 180)
    _draw_text(c, styles["title_xl"], "Tabela Consolidada de Riscos", MARGIN, y - 18, 360)
    _draw_text(c, styles["body"], "Relatorio tecnico detalhando a matriz de criticidade, probabilidade e severidade para suporte a liberacao da atividade.", MARGIN, y - 78, 360)

    table_top = y - 122
    c.setStrokeColor(SLATE_900)
    c.line(MARGIN, table_top, PAGE_W - MARGIN, table_top)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(SLATE_900)
    c.drawString(MARGIN + 8, table_top + 14, "ITEM")
    c.drawString(MARGIN + 68, table_top + 14, "DESCRICAO DO RISCO IDENTIFICADO")
    c.drawString(MARGIN + 368, table_top + 14, "PROB.")
    c.drawString(MARGIN + 430, table_top + 14, "SEV.")
    c.drawString(MARGIN + 474, table_top + 14, "SCORE")
    c.drawString(MARGIN + 532, table_top + 14, "NIVEL")

    row_start = table_top - 12
    for idx, risk in enumerate(view["risks"][:5], start=1):
        row_y = row_start - (idx * 62)
        c.setStrokeColor(SLATE_200)
        c.line(MARGIN, row_y + 50, PAGE_W - MARGIN, row_y + 50)
        c.setFillColor(SLATE_500)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(MARGIN + 8, row_y + 24, str(idx).zfill(2))
        c.setFillColor(SLATE_900)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(MARGIN + 68, row_y + 34, _first(risk.get("hazard"), default="Risco"))
        c.setFont("Helvetica", 8.5)
        c.setFillColor(SLATE_600)
        c.drawString(MARGIN + 68, row_y + 18, _first(risk.get("risk_description"), default="Descricao complementar do risco"))
        c.setFillColor(SLATE_900)
        c.setFont("Helvetica", 10)
        c.drawString(MARGIN + 382, row_y + 24, _to_str(risk.get("probability") or 2))
        c.drawString(MARGIN + 444, row_y + 24, _to_str(risk.get("severity") or 3))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(MARGIN + 484, row_y + 24, _to_str(risk.get("score") or 6))
        level = _normalize_level(risk.get("risk_level"))
        bg, fg = _level_palette(level)
        _draw_round_rect(c, MARGIN + 526, row_y + 14, 52, 18, bg, bg, radius=6)
        c.setFillColor(fg)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(MARGIN + 552, row_y + 19, level.upper())

    summary_y = 84
    _draw_text(c, styles["kicker"], "Analise quantitativa", MARGIN, summary_y + 86, 150)
    _draw_text(c, styles["title_lg"], "Resumo Executivo da APR", MARGIN, summary_y + 68, 260)
    cards = [
        ("Total de riscos", str(len(view["risks"])), "itens"),
        ("Criticos / altos", f"{view['critical']:02d} / {view['high']:02d}", "atencao prioritaria"),
        ("Maior score", max((_to_str(item.get("score")) for item in view["risks"]), default="0"), _first(view["top_risks"][0] if view["top_risks"] else "-")),
    ]
    for idx, (label, value, detail) in enumerate(cards):
        x = MARGIN + (idx * 148)
        _draw_round_rect(c, x, summary_y, 136, 58, colors.white, SLATE_200, radius=10)
        _draw_text(c, styles["small_caps"], label, x + 12, summary_y + 46, 110)
        _draw_text(c, styles["title_md"], value, x + 12, summary_y + 28, 100)
        _draw_text(c, styles["body_muted"], detail, x + 12, summary_y + 12, 110)
    _draw_round_rect(c, PAGE_W - MARGIN - 160, summary_y, 160, 58, SLATE_950, SLATE_950, radius=10)
    _draw_text(c, styles["small_caps"], "Consolidado", PAGE_W - MARGIN - 146, summary_y + 46, 100)
    _draw_text(c, styles["title_lg"], "ALTO", PAGE_W - MARGIN - 146, summary_y + 30, 100)
    _draw_text(c, styles["body_white"], "Exige supervisao continua", PAGE_W - MARGIN - 146, summary_y + 12, 110)
    _draw_footer(c)


def _draw_matrix(c: canvas.Canvas, x: float, y: float, cell: float = 34) -> None:
    matrix = [
        [GREEN_50, GREEN_50, BLUE_50, AMBER_50, RED_50],
        [GREEN_50, GREEN_50, BLUE_50, AMBER_50, RED_50],
        [GREEN_50, BLUE_50, AMBER_50, RED_50, RED_50],
        [BLUE_50, AMBER_50, RED_50, RED_50, RED_50],
        [AMBER_50, RED_50, RED_50, RED_50, RED_50],
    ]
    for row_idx, row in enumerate(matrix):
        for col_idx, fill in enumerate(row):
            px = x + (col_idx * cell)
            py = y + (row_idx * cell)
            _draw_round_rect(c, px, py, cell - 4, cell - 4, fill, fill, radius=4)


def _draw_conclusion_page(c: canvas.Canvas, styles: dict[str, ParagraphStyle], view: dict[str, Any], page_no: int, total_pages: int) -> None:
    _draw_header(c, styles, "Relatorio de Analise Preliminar de Risco", "Documento final", page_no, total_pages)
    y = PAGE_H - 112
    _draw_text(c, styles["title_xl"], "Conclusao de Auditoria e<br/>Validacao Legal", MARGIN, y, 320)
    _draw_text(c, styles["body"], "A consolidacao final dos riscos identificados assegura conformidade com normas regulamentadoras, protocolos internos e criterios de liberacao corporativa.", MARGIN, y - 66, 330)
    _draw_round_rect(c, PAGE_W - MARGIN - 110, y - 52, 110, 66, colors.HexColor("#e8eefc"), colors.HexColor("#e8eefc"), radius=10)
    _draw_text(c, styles["small_caps"], "Codigo do relatorio", PAGE_W - MARGIN - 96, y - 12, 90)
    _draw_text(c, styles["title_md"], view["code"], PAGE_W - MARGIN - 96, y - 28, 90)

    panel_y = y - 236
    _draw_round_rect(c, MARGIN, panel_y, 252, 156, colors.white, SLATE_200, radius=14)
    _draw_text(c, styles["title_md"], "Matriz de Risco Consolidada", MARGIN + 14, panel_y + 136, 180)
    _draw_matrix(c, MARGIN + 22, panel_y + 18)

    _draw_round_rect(c, MARGIN + 270, panel_y + 82, 236, 74, colors.HexColor("#eef3ff"), colors.HexColor("#eef3ff"), radius=12)
    _draw_text(c, styles["title_md"], "Riscos Criticos Identificados", MARGIN + 284, panel_y + 136, 180)
    for idx, item in enumerate(view["top_risks"][:2]):
        _draw_text(c, styles["body_sm"], f"0{idx + 1}. {item}", MARGIN + 286, panel_y + 110 - (idx * 24), 196)
        _draw_round_rect(c, MARGIN + 286, panel_y + 90 - (idx * 24), 76, 14, RED_700, RED_700, radius=7)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(MARGIN + 324, panel_y + 95 - (idx * 24), "PRIORIDADE MAXIMA")

    _draw_round_rect(c, MARGIN + 270, panel_y, 236, 60, colors.HexColor("#eef3ff"), colors.HexColor("#eef3ff"), radius=12)
    _draw_text(c, styles["title_md"], "Estatisticas finais", MARGIN + 284, panel_y + 46, 140)
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(SLATE_950)
    c.drawString(MARGIN + 286, panel_y + 20, str(len(view["risks"])))
    c.setFillColor(RED_700)
    c.drawString(MARGIN + 362, panel_y + 20, str(view["critical"]).zfill(2))
    c.setFillColor(SLATE_950)
    c.drawString(MARGIN + 442, panel_y + 20, str(max(0, len(view["risks"]) - view["critical"])))

    note_y = panel_y - 150
    _draw_round_rect(c, MARGIN, note_y, CONTENT_W, 118, colors.white, SLATE_200, radius=14)
    _draw_text(c, styles["title_md"], "Observacoes Finais do Aprovador", MARGIN + 16, note_y + 94, 240)
    _draw_text(c, styles["body"], "Certifico que a analise apresentada contempla os requisitos tecnicos de seguranca exigidos para a atividade. As medidas mitigadoras listadas nas secoes anteriores devem ser mantidas ate o encerramento do servico.", MARGIN + 16, note_y + 70, CONTENT_W - 32)
    _draw_text(c, styles["body_muted"], f"Verificado digitalmente • {view['approved_by']} • {view['approved_at']}", MARGIN + 16, note_y + 16, 280)

    block_y = 58
    block_w = (CONTENT_W - 24) / 3
    signature_blocks = [
        ("Emissao tecnica", view["responsavel"], view["issued_at"], BLUE_100, BLUE_700, view["code"]),
        ("Aprovacao formal", view["approved_by"], view["approved_at"], GREEN_50, GREEN_700, view["external_id"]),
        ("Selo de autenticidade", view["code"], view["status"], SLATE_100, SLATE_700, "Documento rastreavel"),
    ]
    for idx, (label, name, meta, fill, accent, detail) in enumerate(signature_blocks):
        block_x = MARGIN + (idx * (block_w + 12))
        _draw_round_rect(c, block_x, block_y, block_w, 74, colors.white, SLATE_200, radius=12)
        _draw_round_rect(c, block_x + 12, block_y + 18, 34, 34, fill, fill, radius=10)
        c.setFillColor(accent)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(block_x + 29, block_y + 30, _initials(_first(name, default="SC")))
        _draw_text(c, styles["small_caps"], label, block_x + 56, block_y + 58, block_w - 68)
        _draw_text(c, styles["body_sm"], name, block_x + 56, block_y + 40, block_w - 68)
        _draw_text(c, styles["body_muted"], f"{meta} • {detail}", block_x + 56, block_y + 22, block_w - 68)
    c.setFillColor(BLUE_700)
    c.rect(MARGIN, 44, 200, 3, fill=1, stroke=0)
    c.setFillColor(RED_700)
    c.rect(MARGIN + 200, 44, 160, 3, fill=1, stroke=0)
    _draw_footer(c)


def _render_builder_pdf(documento: dict, caminho_saida: str) -> None:
    styles = _styles()
    view = _builder_view(documento)
    step_count = max(1, len(view["steps"]))
    total_pages = 4 + step_count
    c = canvas.Canvas(caminho_saida, pagesize=A4)
    c.setTitle(view["code"])

    _draw_cover_page(c, styles, view, 1, total_pages)
    c.showPage()
    _draw_context_page(c, styles, view, 2, total_pages)
    c.showPage()

    current_page = 3
    for step in view["steps"]:
        _draw_step_page(c, styles, view, step, current_page, total_pages)
        c.showPage()
        current_page += 1

    _draw_risk_table_page(c, styles, view, current_page, total_pages)
    c.showPage()
    current_page += 1
    _draw_conclusion_page(c, styles, view, current_page, total_pages)
    c.save()


def _render_fallback_pdf(documento: Any, caminho_saida: str) -> None:
    doc = SimpleDocTemplate(
        caminho_saida,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()
    title = styles["Title"]
    body = ParagraphStyle("fallback", parent=styles["BodyText"], fontName="Courier", fontSize=8.5, leading=10.5)
    elements = [Paragraph("ANALISE PRELIMINAR DE RISCO (APR)", title), Spacer(1, 12)]
    for line in _to_str(documento).split("\n"):
        elements.append(_safe_para(line, body))
    doc.build(elements)


def gerar_pdf_apr(documento: Any, caminho_saida: str):
    if _is_builder_format(documento):
        _render_builder_pdf(documento, caminho_saida)
        return
    _render_fallback_pdf(documento, caminho_saida)
