from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path
from typing import Iterable, Dict, Any, Mapping

SCHEMA_VERSION = 1
SCHEMA_DATE = "2026-01-23"
SHEET_NAME = "Sheet1"
LIST_SEPARATOR = ";"
LOCALE = "pt-BR"
APP_NAME = "Engenharia APR"
CONTRACT_NAME = "APR_CONTRACT_V1"
CACHE_CONTROL = "public, max-age=300, must-revalidate"

APR_REQUIRED_FIELDS = ["worksite", "sector", "responsible", "date", "activity_id"]
APR_MIN_ITEMS = {"hazards": 1, "measures": 1}
RISK_MATRIX = {
    "probability": {"min": 1, "max": 5},
    "severity": {"min": 1, "max": 5},
    "calc": "p*s",
    "bands": [
        {"min": 1, "max": 5, "level": "baixo"},
        {"min": 6, "max": 12, "level": "medio"},
        {"min": 13, "max": 25, "level": "alto"},
    ],
}

EPI_FIELDS = ["id", "name", "category", "certificate_code", "is_mandatory", "tags", "notes"]
EPI_REQUIRED = {"id", "epi"}
EPI_OPTIONAL = {"descricao", "normas"}

PERIGO_FIELDS = [
    "id",
    "name",
    "hazard_type",
    "default_severity",
    "default_probability",
    "tags",
    "notes",
]
PERIGO_REQUIRED = {"id", "perigo"}
PERIGO_OPTIONAL = {"consequencias", "salvaguardas"}

ATIVIDADES_FIELDS = ["id", "name", "category", "description", "regulation", "tags"]
ATIVIDADES_REQUIRED = {"atividade_id", "atividade", "ordem_passo", "descricao_passo"}
ATIVIDADES_OPTIONAL = {
    "local",
    "funcao",
    "perigos",
    "riscos",
    "medidas_controle",
    "epis",
    "normas",
}

EXCEL_FILES = (
    "epis_apr_modelo_validado.xlsx",
    "perigos_apr_modelo_validado.xlsx",
    "atividades_passos_apr_modelo_validado.xlsx",
)

EXCEL_MAPPING = {
    "sheet": SHEET_NAME,
    "list_separator": LIST_SEPARATOR,
    "extras_allowed": False,
    "files": {
        "epis_apr_modelo_validado.xlsx": {
            "entity": "EPI",
            "required_columns": sorted(EPI_REQUIRED),
            "optional_columns": sorted(EPI_OPTIONAL),
            "column_map": {
                "id": {
                    "entity": "EPI",
                    "field": "catalogs.epis.items[].id",
                    "note": "excel_id (nao persistido no banco)",
                },
                "epi": {"entity": "EPI", "field": "catalogs.epis.items[].name"},
                "descricao": {
                    "entity": "EPI",
                    "field": None,
                    "note": "nao existe campo canonico correspondente no contrato v1",
                },
                "normas": {
                    "entity": "EPI",
                    "field": None,
                    "note": "nao existe campo canonico correspondente no contrato v1",
                },
            },
            "fields_not_in_excel": ["category", "certificate_code", "is_mandatory", "tags", "notes"],
        },
        "perigos_apr_modelo_validado.xlsx": {
            "entity": "Perigo",
            "required_columns": sorted(PERIGO_REQUIRED),
            "optional_columns": sorted(PERIGO_OPTIONAL),
            "column_map": {
                "id": {
                    "entity": "Perigo",
                    "field": "catalogs.hazards.items[].id",
                    "note": "excel_id (nao persistido no banco)",
                },
                "perigo": {"entity": "Perigo", "field": "catalogs.hazards.items[].name"},
                "consequencias": {
                    "entity": "Perigo",
                    "field": None,
                    "note": "nao existe campo canonico correspondente no contrato v1",
                },
                "salvaguardas": {
                    "entity": "Perigo",
                    "field": None,
                    "note": "nao existe campo canonico correspondente no contrato v1",
                },
            },
            "fields_not_in_excel": [
                "hazard_type",
                "default_severity",
                "default_probability",
                "tags",
                "notes",
            ],
        },
        "atividades_passos_apr_modelo_validado.xlsx": {
            "entities": ["APR", "Passo"],
            "required_columns": sorted(ATIVIDADES_REQUIRED),
            "optional_columns": sorted(ATIVIDADES_OPTIONAL),
            "column_map": {
                "atividade_id": {
                    "entity": "APR",
                    "field": "catalogs.activities.items[].id",
                    "note": "gera agrupamento de APR",
                },
                "atividade": {
                    "entity": "APR",
                    "field": "catalogs.activities.items[].name",
                },
                "local": {
                    "entity": "APR",
                    "field": None,
                    "note": "compoe APR.descricao",
                },
                "funcao": {
                    "entity": "APR",
                    "field": None,
                    "note": "compoe APR.descricao",
                },
                "ordem_passo": {
                    "entity": "Passo",
                    "field": "aprs.steps.step_order",
                },
                "descricao_passo": {
                    "entity": "Passo",
                    "field": "aprs.steps.description",
                },
                "perigos": {
                    "entity": "Passo",
                    "field": "aprs.steps.hazards",
                },
                "riscos": {
                    "entity": "Passo",
                    "field": None,
                    "note": "nao existe campo canonico correspondente no contrato v1",
                },
                "medidas_controle": {
                    "entity": "Passo",
                    "field": "aprs.steps.measures",
                },
                "epis": {
                    "entity": "Passo",
                    "field": "aprs.steps.epis",
                },
                "normas": {
                    "entity": "Passo",
                    "field": "aprs.steps.regulations",
                },
            },
            "fields_not_in_excel": ["category", "description", "regulation", "tags"],
        },
    },
}

def _latest_mtime() -> datetime:
    base_dir = Path(__file__).resolve().parent
    paths = [Path(__file__).resolve()]
    for name in EXCEL_FILES:
        path = base_dir / name
        if path.exists():
            paths.append(path)
    return max(datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc) for p in paths)


def _contract_cache_headers(contract: Dict[str, Any]) -> Dict[str, str]:
    payload = json.dumps(
        contract,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    etag = hashlib.sha256(payload).hexdigest()
    last_modified = format_datetime(_latest_mtime(), usegmt=True)
    return {
        "ETag": f"\"{etag}\"",
        "Last-Modified": last_modified,
        "Cache-Control": CACHE_CONTROL,
    }


def _is_not_modified(request_headers: Mapping[str, str], response_headers: Mapping[str, str]) -> bool:
    etag = response_headers.get("ETag")
    if etag:
        if_none_match = request_headers.get("if-none-match")
        if if_none_match and if_none_match.strip() == etag:
            return True

    if_modified_since = request_headers.get("if-modified-since")
    last_modified = response_headers.get("Last-Modified")
    if if_modified_since and last_modified:
        try:
            ims_dt = parsedate_to_datetime(if_modified_since)
            lm_dt = parsedate_to_datetime(last_modified)
            if ims_dt is None or lm_dt is None:
                return False
            if ims_dt.tzinfo is None:
                ims_dt = ims_dt.replace(tzinfo=timezone.utc)
            if lm_dt.tzinfo is None:
                lm_dt = lm_dt.replace(tzinfo=timezone.utc)
            if lm_dt <= ims_dt:
                return True
        except Exception:
            return False

    return False


def get_contract_cached(
    request_headers: Mapping[str, str],
) -> tuple[Dict[str, Any], Dict[str, str], bool]:
    contract = get_contract()
    headers = _contract_cache_headers(contract)
    not_modified = _is_not_modified(request_headers, headers)
    return contract, headers, not_modified

def _file_meta(filename: str) -> Dict[str, Any]:
    path = Path(__file__).resolve().parent / filename
    if not path.exists():
        return {"hash": None, "updated_at": None}

    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)

    updated_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return {
        "hash": f"sha256:{hasher.hexdigest()}",
        "updated_at": updated_at.isoformat().replace("+00:00", "Z"),
    }


def get_contract() -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "version_date": SCHEMA_DATE,
        "locale": LOCALE,
        "app": {
            "name": APP_NAME,
            "contract_name": CONTRACT_NAME,
        },
        "catalogs": {
            "epis": {
                "fields": EPI_FIELDS,
                "items": [],
            },
            "hazards": {
                "fields": PERIGO_FIELDS,
                "items": [],
            },
            "activities": {
                "fields": ATIVIDADES_FIELDS,
                "items": [],
            },
        },
        "mappings": {
            "activity_to_hazards": [],
            "hazard_to_epis": [],
        },
        "rules": {
            "apr": {
                "required_fields": APR_REQUIRED_FIELDS,
                "min_items": APR_MIN_ITEMS,
            },
            "risk_matrix": RISK_MATRIX,
        },
        "excel_mapping": EXCEL_MAPPING,
        "files": {
            "epis_apr_modelo_validado.xlsx": _file_meta("epis_apr_modelo_validado.xlsx"),
            "perigos_apr_modelo_validado.xlsx": _file_meta("perigos_apr_modelo_validado.xlsx"),
            "atividades_passos_apr_modelo_validado.xlsx": _file_meta("atividades_passos_apr_modelo_validado.xlsx"),
        },
    }


def get_excel_hashes() -> Dict[str, Dict[str, Any]]:
    return {
        "epis_apr_modelo_validado.xlsx": _file_meta("epis_apr_modelo_validado.xlsx"),
        "perigos_apr_modelo_validado.xlsx": _file_meta("perigos_apr_modelo_validado.xlsx"),
        "atividades_passos_apr_modelo_validado.xlsx": _file_meta("atividades_passos_apr_modelo_validado.xlsx"),
    }


def _norm_cols(cols: Iterable) -> set[str]:
    return {str(c).strip().lower() for c in cols}


def _validate_columns(
    cols: Iterable,
    required: set[str],
    optional: set[str],
    context: str,
) -> None:
    normalized = _norm_cols(cols)
    missing = sorted(c for c in required if c not in normalized)
    if missing:
        missing_list = ", ".join(missing)
        raise ValueError(
            f"schema_version={SCHEMA_VERSION} ({context}) requer colunas: {missing_list}"
        )

    allowed = required | optional
    extra = sorted(c for c in normalized if c not in allowed)
    if extra:
        extra_list = ", ".join(extra)
        raise ValueError(
            f"schema_version={SCHEMA_VERSION} ({context}) colunas nao permitidas: {extra_list}"
        )


def validate_epis_df(df) -> None:
    _validate_columns(df.columns, EPI_REQUIRED, EPI_OPTIONAL, "epis")


def validate_perigos_df(df) -> None:
    _validate_columns(df.columns, PERIGO_REQUIRED, PERIGO_OPTIONAL, "perigos")


def validate_atividades_df(df) -> None:
    _validate_columns(df.columns, ATIVIDADES_REQUIRED, ATIVIDADES_OPTIONAL, "atividades")
