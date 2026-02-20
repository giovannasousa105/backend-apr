from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Any, Iterable

from consolidation.pdf import gerar_pdf_apr
from api_errors import ApiError, missing_fields_error
from risk_engine import is_risk_item_valid
from text_normalizer import normalize_text

PDF_TEMPLATE_VERSION = "1.0"

_DANGEROUS_ENERGIES_ORDER = [
    ("hydraulic", "Hidraulica"),
    ("residual", "Residual"),
    ("kinetic", "Cinetica"),
    ("mechanical", "Mecanica"),
    ("electrical", "Eletrica"),
    ("gravitational_potential", "Potencial gravitacional"),
    ("thermal", "Termica"),
    ("pneumatic", "Pneumatica"),
]


def _sanitize_text(value: Any) -> str:
    normalized = normalize_text(value, keep_newlines=True, origin="user", field=None)
    return normalized if normalized is not None else ""


def _split_list(value: str) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[;,]", str(value))
    return [_sanitize_text(p) for p in parts if str(p).strip()]


def _has_any(values: Iterable[str]) -> bool:
    return any(v for v in values if str(v).strip())


def validate_apr_for_pdf(apr: Any, passos: list[Any], risk_items: list[Any] | None = None) -> None:
    missing = []
    if not getattr(apr, "sector", None):
        missing.append("obra")
    if not getattr(apr, "worksite", None):
        missing.append("local")
    if not getattr(apr, "responsible", None):
        missing.append("responsavel")
    if not getattr(apr, "date", None):
        missing.append("data")
    if not getattr(apr, "activity_id", None):
        missing.append("atividade_id")
    if not getattr(apr, "activity_name", None):
        missing.append("atividade_nome")
    if not getattr(apr, "titulo", None):
        missing.append("titulo")
    if not getattr(apr, "risco", None):
        missing.append("risco")
    if not getattr(apr, "descricao", None):
        missing.append("descricao")

    if missing:
        raise missing_fields_error(missing)

    if not passos:
        raise ApiError(
            status_code=400,
            code="min_steps",
            message="APR precisa ter pelo menos 1 passo antes de gerar PDF",
            field="passos",
        )

    for p in passos:
        perigos = _split_list(getattr(p, "perigos", ""))
        medidas = _split_list(getattr(p, "medidas_controle", ""))
        ordem = getattr(p, "ordem", None)
        prefix = f"Passo {ordem}" if ordem is not None else "Passo"
        if len(perigos) < 1:
            raise ApiError(
                status_code=400,
                code="min_hazard",
                message=f"{prefix} precisa ter pelo menos 1 perigo antes de gerar PDF",
                field=f"passos[{ordem}].perigos" if ordem is not None else "passos.perigos",
            )
        if len(medidas) < 1:
            raise ApiError(
                status_code=400,
                code="min_control",
                message=f"{prefix} precisa ter pelo menos 1 medida antes de gerar PDF",
                field=f"passos[{ordem}].medidas_controle"
                if ordem is not None
                else "passos.medidas_controle",
            )

    if risk_items is not None:
        for item in risk_items:
            if not is_risk_item_valid(item):
                raise ApiError(
                    status_code=400,
                    code="risk_score_invalid",
                    message="Existe risco sem score valido (probability/severity devem ser 1-5)",
                    field="risk_items",
                )


def build_apr_document(apr: Any, passos: list[Any], risk_items: list[Any] | None = None) -> dict:
    base_dir = Path(__file__).resolve().parent
    evidence_dir = base_dir / "uploads" / "step_evidence"
    checklist = getattr(apr, "dangerous_energies_checklist", None) or {}
    energies = [
        {
            "energia": label,
            "marcado": True,
        }
        for key, label in _DANGEROUS_ENERGIES_ORDER
        if bool(checklist.get(key, False))
    ]
    step_order_by_id = {getattr(p, "id", None): getattr(p, "ordem", None) for p in passos}
    matrix = []
    for item in risk_items or []:
        matrix.append(
            {
                "step_order": step_order_by_id.get(getattr(item, "step_id", None)),
                "hazard": _sanitize_text(getattr(getattr(item, "hazard", None), "perigo", None)),
                "risk_description": _sanitize_text(getattr(item, "risk_description", None)),
                "probability": getattr(item, "probability", None),
                "severity": getattr(item, "severity", None),
                "score": getattr(item, "score", None),
                "risk_level": _sanitize_text(getattr(item, "risk_level", None)),
            }
        )
    return {
        "tipo_documento": "APR",
        "versao_modelo": "1.0",
        "gerado_em": datetime.utcnow().isoformat() + "Z",
        "documentos": [
            {
                "apr": {
                    "atividade_id": _sanitize_text(getattr(apr, "activity_id", None)),
                    "atividade": _sanitize_text(
                        getattr(apr, "activity_name", None) or getattr(apr, "titulo", None)
                    ),
                    "obra": _sanitize_text(getattr(apr, "sector", None)),
                    "local": _sanitize_text(getattr(apr, "worksite", None)),
                    "responsavel": _sanitize_text(getattr(apr, "responsible", None)),
                    "data": _sanitize_text(
                        apr.date.isoformat() if getattr(apr, "date", None) else None
                    ),
                    "dangerous_energies_checklist": energies,
                    "risk_matrix": matrix,
                },
                "passos": [
                    {
                        "ordem": p.ordem,
                        "descricao": _sanitize_text(p.descricao),
                        "perigos": _split_list(p.perigos),
                        "riscos": _split_list(p.riscos),
                        "medidas_controle": _split_list(p.medidas_controle),
                        "epis": _split_list(p.epis),
                        "normas": _split_list(p.normas),
                        "technical_evidence": (
                            {
                                "type": getattr(p, "evidence_type", None) or "image",
                                "caption": _sanitize_text(getattr(p, "evidence_caption", None)),
                                "uploaded_at": getattr(p, "evidence_uploaded_at", None),
                                "path": (
                                    str(evidence_dir / getattr(p, "evidence_filename"))
                                    if getattr(p, "evidence_filename", None)
                                    else None
                                ),
                            }
                            if getattr(p, "evidence_filename", None)
                            else None
                        ),
                    }
                    for p in passos
                ],
            }
        ],
    }


def write_apr_pdf(apr: Any, passos: list[Any], filename: str, risk_items: list[Any] | None = None) -> Path:
    documento = build_apr_document(apr, passos, risk_items)
    base_dir = Path(__file__).resolve().parent
    exports_dir = base_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    path = exports_dir / filename
    gerar_pdf_apr(documento, str(path))
    return path
