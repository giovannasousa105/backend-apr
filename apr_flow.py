from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
import re

import pandas as pd

from excel_contract import validate_atividades_df
from text_normalizer import normalize_text, normalize_list


@dataclass
class ActivityRow:
    atividade_id: str
    atividade: str
    local: str | None
    funcao: str | None
    ordem_passo: int
    descricao_passo: str
    perigos: List[str]
    riscos: List[str]
    medidas_controle: List[str]
    epis: List[str]
    normas: List[str]


_CACHE: dict[str, Any] = {
    "mtime": None,
    "activities": [],
    "by_id": {},
}


def _norm_id(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        if float(value).is_integer():
            return str(int(value))
    return normalize_text(value, keep_newlines=False, origin="excel", field="atividade_id")


def _split_list(value: Any, field: str) -> List[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return [v for v in normalize_list(value, origin="excel", field=field) if v]
    text = normalize_text(value, keep_newlines=False, origin="excel", field=field) or ""
    if not text:
        return []
    parts = re.split(r"[;,]", text)
    return [
        normalize_text(p, keep_newlines=False, origin="excel", field=field) or ""
        for p in parts
        if str(p).strip()
    ]


def _load_df(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    validate_atividades_df(df)
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _build_cache(path: Path) -> None:
    df = _load_df(path)

    by_id: Dict[str, Dict[str, Any]] = {}

    for _, row in df.iterrows():
        activity_id = _norm_id(row.get("atividade_id"))
        if not activity_id:
            continue

        atividade = (
            normalize_text(row.get("atividade"), keep_newlines=False, origin="excel", field="atividade")
            or ""
        )
        if not atividade:
            atividade = f"Atividade {activity_id}"

        entry = by_id.setdefault(
            activity_id,
            {
                "activity": {
                    "id": activity_id,
                    "name": atividade,
                    "category": None,
                    "description": None,
                    "regulation": None,
                    "tags": [],
                },
                "rows": [],
            },
        )

        # Mantem o primeiro nome valido como principal
        if entry["activity"].get("name") in (None, "", f"Atividade {activity_id}") and atividade:
            entry["activity"]["name"] = atividade

        row_obj = ActivityRow(
            atividade_id=activity_id,
            atividade=atividade,
            local=normalize_text(row.get("local"), keep_newlines=False, origin="excel", field="local"),
            funcao=normalize_text(row.get("funcao"), keep_newlines=False, origin="excel", field="funcao"),
            ordem_passo=int(row.get("ordem_passo")) if row.get("ordem_passo") is not None else 0,
            descricao_passo=(
                normalize_text(row.get("descricao_passo"), keep_newlines=True, origin="excel", field="descricao_passo")
                or ""
            ),
            perigos=_split_list(row.get("perigos"), "perigos"),
            riscos=_split_list(row.get("riscos"), "riscos"),
            medidas_controle=_split_list(row.get("medidas_controle"), "medidas_controle"),
            epis=_split_list(row.get("epis"), "epis"),
            normas=_split_list(row.get("normas"), "normas"),
        )
        entry["rows"].append(row_obj)

    activities = [v["activity"] for v in by_id.values()]
    activities.sort(key=lambda item: (_sort_key(item.get("id"))))

    _CACHE["mtime"] = path.stat().st_mtime
    _CACHE["by_id"] = by_id
    _CACHE["activities"] = activities


def _sort_key(value: Any) -> tuple:
    if value is None:
        return (1, "")
    try:
        return (0, int(value))
    except Exception:
        return (1, str(value))


def _get_cache() -> dict[str, Any]:
    base_dir = Path(__file__).resolve().parent
    path = base_dir / "atividades_passos_apr_modelo_validado.xlsx"
    if not path.exists():
        return {"activities": [], "by_id": {}}

    mtime = path.stat().st_mtime
    if _CACHE["mtime"] != mtime:
        _build_cache(path)
    return _CACHE


def list_activities() -> List[Dict[str, Any]]:
    cache = _get_cache()
    return list(cache.get("activities") or [])


def get_activity_suggestions(activity_id: str) -> Dict[str, Any] | None:
    cache = _get_cache()
    key = _norm_id(activity_id)
    if not key:
        return None
    entry = cache.get("by_id", {}).get(key)
    if not entry:
        return None

    rows: List[ActivityRow] = entry.get("rows", [])
    steps = []
    hazards_set = set()
    risks_set = set()
    measures_set = set()
    epis_set = set()
    regulations_set = set()

    for row in sorted(rows, key=lambda r: r.ordem_passo or 0):
        hazards_set.update(row.perigos)
        risks_set.update(row.riscos)
        measures_set.update(row.medidas_controle)
        epis_set.update(row.epis)
        regulations_set.update(row.normas)

        steps.append(
            {
                "step_order": row.ordem_passo or 0,
                "description": row.descricao_passo or "",
                "hazards": row.perigos,
                "risks": row.riscos,
                "measures": row.medidas_controle,
                "epis": row.epis,
                "regulations": row.normas,
            }
        )

    suggestions = {
        "hazards": sorted(hazards_set),
        "risks": sorted(risks_set),
        "measures": sorted(measures_set),
        "epis": sorted(epis_set),
        "regulations": sorted(regulations_set),
    }

    return {
        "activity": entry["activity"],
        "suggestions": suggestions,
        "steps": steps,
    }
