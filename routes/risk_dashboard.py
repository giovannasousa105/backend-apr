from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import math
import os
from datetime import date, datetime, time
from functools import lru_cache
from typing import Any, Dict, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from auth import get_current_user
from database import SessionLocal
from models import User
from rbac import normalize_role

router = APIRouter(prefix="/api", tags=["dashboard"])

Period = Literal["days", "weeks", "months", "year"]


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except Exception:
        return default
    return value if value > 0 else default


DEFAULT_TZ = "America/Sao_Paulo"
CACHE_TTL_SECONDS = _env_int("RISK_DASHBOARD_CACHE_TTL_SECONDS", 120)
STALE_CACHE_TTL_SECONDS = _env_int("RISK_DASHBOARD_STALE_TTL_SECONDS", 86400)
CACHE_CONTROL_VALUE = (
    f"private, max-age=0, s-maxage=0, stale-while-revalidate={CACHE_TTL_SECONDS}"
)
RAW_ALLOWED_ROLES = {"admin", "tecnico", "gestor_seguranca", "engineer", "auditor"}


CLASSIFICATION = {
    "method": "PXS",
    "ranges": [
        {"label": "baixo", "min": 1, "max": 5},
        {"label": "medio", "min": 6, "max": 12},
        {"label": "alto", "min": 13, "max": 25},
    ],
}

COLORS = {
    "baixo": "#22c55e",
    "medio": "#f59e0b",
    "alto": "#ef4444",
}


def to_range_timestamps(start: date, end: date, tz: str) -> tuple[datetime, datetime, str]:
    try:
        z = ZoneInfo(tz)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=400, detail="Timezone invalido") from exc
    start_dt = datetime.combine(start, time.min, tzinfo=z)
    end_dt = datetime.combine(end, time.max, tzinfo=z)

    if end_dt < start_dt:
        raise HTTPException(status_code=400, detail="end deve ser >= start")

    generated_at = datetime.now(tz=z).isoformat()
    return start_dt, end_dt, generated_at


def clamp_pagination(page: int, page_size: int) -> tuple[int, int, int]:
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    offset = (page - 1) * page_size
    return page, page_size, offset


def granularity(period: Period) -> str:
    return {"days": "day", "weeks": "week", "months": "month", "year": "year"}[period]


def _normalize_level(score: int) -> str:
    if score >= 13:
        return "alto"
    if score >= 6:
        return "medio"
    return "baixo"


def make_cache_key(
    *,
    company_id: int,
    period: str,
    start: str,
    end: str,
    tz: str,
    raw_requested: bool,
    raw_effective: bool,
    page: int,
    page_size: int,
) -> str:
    base = (
        f"riskdash:v3:cid={company_id}:p={period}:s={start}:e={end}:tz={tz}"
        f":rq={int(raw_requested)}:re={int(raw_effective)}"
    )
    if raw_effective:
        base += f":pg={page}:ps={page_size}"
    return base


def _fresh_key(base_key: str) -> str:
    return f"{base_key}:fresh"


def _stale_key(base_key: str) -> str:
    return f"{base_key}:stale"


def _month_keys_for_range(start: date, end: date) -> list[str]:
    current_year = start.year
    current_month = start.month
    last_year = end.year
    last_month = end.month
    months: list[str] = []

    while (current_year < last_year) or (
        current_year == last_year and current_month <= last_month
    ):
        months.append(f"{current_year:04d}-{current_month:02d}")
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1
    return months


def compute_etag(payload: dict, salt: str = "riskdash-v3") -> str:
    source: dict[str, Any] = payload
    meta = source.get("meta")
    if isinstance(meta, dict) and "generatedAt" in meta:
        meta_for_hash = {k: v for k, v in meta.items() if k != "generatedAt"}
        source = {**source, "meta": meta_for_hash}

    canonical = json.dumps(
        source, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )
    digest = hashlib.sha256((salt + canonical).encode("utf-8")).hexdigest()
    return f"\"{digest}\""


def _etag_matches(if_none_match: str | None, etag: str) -> bool:
    if not if_none_match:
        return False

    def normalize_token(token: str) -> str:
        value = token.strip()
        if value.startswith("W/"):
            value = value[2:].strip()
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            value = value[1:-1]
        return value

    candidates = [token.strip() for token in if_none_match.split(",")]
    if "*" in candidates:
        return True

    normalized_etag = normalize_token(etag)
    return any(normalize_token(candidate) == normalized_etag for candidate in candidates)


@lru_cache(maxsize=1)
def get_redis_client() -> Redis | None:
    redis_url = (os.getenv("REDIS_URL") or "").strip()
    if not redis_url:
        return None
    return Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)


async def _redis_get(redis: Redis | None, key: str) -> str | None:
    if redis is None:
        return None
    try:
        return await redis.get(key)
    except Exception:
        return None


async def _redis_setex(redis: Redis | None, key: str, ttl: int, value: str) -> None:
    if redis is None:
        return
    try:
        await redis.setex(key, ttl, value)
    except Exception:
        return


async def _redis_sadd(redis: Redis | None, key: str, value: str) -> None:
    if redis is None:
        return
    try:
        await redis.sadd(key, value)
    except Exception:
        return


async def _redis_expire(redis: Redis | None, key: str, ttl: int) -> None:
    if redis is None:
        return
    try:
        await redis.expire(key, ttl)
    except Exception:
        return


async def _redis_smembers(redis: Redis | None, key: str) -> set[str]:
    if redis is None:
        return set()
    try:
        values = await redis.smembers(key)
        return set(values) if values else set()
    except Exception:
        return set()


async def _redis_delete(redis: Redis | None, *keys: str) -> None:
    if redis is None or not keys:
        return
    try:
        await redis.delete(*keys)
    except Exception:
        return


async def invalidate_risk_dashboard_cache(
    redis: Redis | None,
    company_id: int,
    event_dt: datetime,
    tz: str = DEFAULT_TZ,
) -> None:
    if redis is None:
        return

    try:
        zone = ZoneInfo(tz)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo(DEFAULT_TZ)

    if event_dt.tzinfo is None:
        event_dt = event_dt.replace(tzinfo=ZoneInfo("UTC"))
    month = event_dt.astimezone(zone).strftime("%Y-%m")

    month_index_key = f"idx:cid={company_id}:month={month}"
    base_keys = await _redis_smembers(redis, month_index_key)
    if not base_keys:
        return

    delete_keys: list[str] = [month_index_key]
    for base_key in base_keys:
        delete_keys.append(_fresh_key(base_key))
        delete_keys.append(_stale_key(base_key))

    await _redis_delete(redis, *delete_keys)


SQL_KPIS = text(
    """
WITH base AS (
  SELECT
    r.company_id,
    r.apr_id,
    r.updated_at,
    COALESCE(r.score, (r.probability * r.severity)) AS score_final
  FROM risk_items r
  WHERE r.company_id = :company_id
    AND r.updated_at >= :start_ts
    AND r.updated_at <= :end_ts
)
SELECT
  COUNT(*)::int AS total_riscos,
  COUNT(DISTINCT apr_id)::int AS aprs_monitoradas,
  SUM(CASE WHEN score_final BETWEEN 1 AND 5 THEN 1 ELSE 0 END)::int AS risco_baixo,
  SUM(CASE WHEN score_final BETWEEN 6 AND 12 THEN 1 ELSE 0 END)::int AS risco_medio,
  SUM(CASE WHEN score_final BETWEEN 13 AND 25 THEN 1 ELSE 0 END)::int AS risco_alto_critico,
  ROUND(AVG(score_final)::numeric, 1) AS score_medio,
  MAX(updated_at) AS ultima_atualizacao
FROM base;
"""
)

SQL_RISK_BY_APR = text(
    """
WITH base AS (
  SELECT
    r.apr_id,
    COALESCE(r.score, (r.probability * r.severity)) AS score_final
  FROM risk_items r
  WHERE r.company_id = :company_id
    AND r.updated_at >= :start_ts
    AND r.updated_at <= :end_ts
)
SELECT
  a.id AS apr_id,
  a.titulo AS apr_label,
  COUNT(*) FILTER (WHERE score_final BETWEEN 1 AND 5)::int AS baixo,
  COUNT(*) FILTER (WHERE score_final BETWEEN 6 AND 12)::int AS medio,
  COUNT(*) FILTER (WHERE score_final BETWEEN 13 AND 25)::int AS alto,
  COUNT(*)::int AS total
FROM base b
JOIN aprs a ON a.id = b.apr_id
WHERE a.company_id = :company_id
GROUP BY a.id, a.titulo
ORDER BY total DESC
LIMIT 50;
"""
)

SQL_SERIES_TEMPLATE = """
WITH base AS (
  SELECT
    r.updated_at,
    COALESCE(r.score, (r.probability * r.severity)) AS score_final
  FROM risk_items r
  WHERE r.company_id = :company_id
    AND r.updated_at >= :start_ts
    AND r.updated_at <= :end_ts
),
bucketed AS (
  SELECT
    date_trunc('{gran}', updated_at) AS bucket,
    score_final
  FROM base
)
SELECT
  bucket,
  COUNT(*) FILTER (WHERE score_final BETWEEN 1 AND 5)::int AS baixo,
  COUNT(*) FILTER (WHERE score_final BETWEEN 6 AND 12)::int AS medio,
  COUNT(*) FILTER (WHERE score_final BETWEEN 13 AND 25)::int AS alto,
  COUNT(*)::int AS total,
  ROUND(AVG(score_final)::numeric, 1) AS score_medio
FROM bucketed
GROUP BY bucket
ORDER BY bucket;
"""

SQL_RAW_COUNT = text(
    """
SELECT COUNT(*)::int AS total_rows
FROM risk_items r
WHERE r.company_id = :company_id
  AND r.updated_at >= :start_ts
  AND r.updated_at <= :end_ts;
"""
)

SQL_RAW_DATA = text(
    """
SELECT
  r.id AS risk_id,
  r.apr_id,
  a.titulo AS apr_label,
  r.step_id,
  r.hazard_id,
  r.risk_description,
  r.probability,
  r.severity,
  COALESCE(r.score, (r.probability * r.severity))::int AS score_final,
  r.risk_level,
  r.updated_at AS event_at,
  p.atualizado_em AS step_updated_at
FROM risk_items r
JOIN aprs a ON a.id = r.apr_id AND a.company_id = :company_id
LEFT JOIN passos p ON p.id = r.step_id AND p.company_id = :company_id
WHERE r.company_id = :company_id
  AND r.updated_at >= :start_ts
  AND r.updated_at <= :end_ts
ORDER BY r.updated_at DESC
LIMIT :limit OFFSET :offset;
"""
)

SQL_RAW_EXPORT = text(
    """
SELECT
  r.id AS risk_id,
  r.apr_id,
  a.titulo AS apr_label,
  r.step_id,
  r.hazard_id,
  r.risk_description,
  r.probability,
  r.severity,
  COALESCE(r.score, (r.probability * r.severity))::int AS score_final,
  r.risk_level,
  r.updated_at AS event_at,
  p.atualizado_em AS step_updated_at
FROM risk_items r
JOIN aprs a ON a.id = r.apr_id AND a.company_id = :company_id
LEFT JOIN passos p ON p.id = r.step_id AND p.company_id = :company_id
WHERE r.company_id = :company_id
  AND r.updated_at >= :start_ts
  AND r.updated_at <= :end_ts
ORDER BY r.updated_at DESC;
"""
)


def _fetch_one(sql_stmt, params: dict) -> dict:
    db: Session = SessionLocal()
    try:
        row = db.execute(sql_stmt, params).mappings().first()
        return dict(row) if row else {}
    finally:
        db.close()


def _fetch_all(sql_stmt, params: dict) -> list[dict]:
    db: Session = SessionLocal()
    try:
        rows = db.execute(sql_stmt, params).mappings().all()
        return [dict(r) for r in rows]
    finally:
        db.close()


@router.get("/risk-dashboard")
async def risk_dashboard(
    request: Request,
    period: Period = Query("months"),
    start: date = Query(..., description="YYYY-MM-DD"),
    end: date = Query(..., description="YYYY-MM-DD"),
    tz: str = Query(DEFAULT_TZ),
    includeRaw: bool = Query(False),
    page: int = Query(1),
    pageSize: int = Query(10),
    export: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
):
    company_id = current_user.company_id
    if not company_id:
        raise HTTPException(status_code=403, detail="Usuario sem company_id")

    start_ts, end_ts, generated_at = to_range_timestamps(start, end, tz)
    params = {
        "company_id": int(company_id),
        "start_ts": start_ts,
        "end_ts": end_ts,
    }

    raw_requested = bool(includeRaw)
    current_role = normalize_role(getattr(current_user, "role", None))
    raw_allowed = current_role in RAW_ALLOWED_ROLES
    include_raw_effective = raw_requested and raw_allowed

    p, ps, offset = clamp_pagination(page, pageSize)

    if (export or "").lower() == "csv":
        export_rows = await run_in_threadpool(_fetch_all, SQL_RAW_EXPORT, params)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "riskId",
                "aprId",
                "aprLabel",
                "stepId",
                "hazardId",
                "riskDescription",
                "probability",
                "severity",
                "score",
                "riskLevel",
                "eventAt",
                "updatedAt",
                "createdAt",
                "stepUpdatedAt",
            ]
        )

        for row in export_rows:
            score = int(row["score_final"] or 0)
            level = _normalize_level(score)
            event_at = row.get("event_at")
            writer.writerow(
                [
                    row.get("risk_id"),
                    row.get("apr_id"),
                    row.get("apr_label"),
                    row.get("step_id"),
                    row.get("hazard_id"),
                    row.get("risk_description"),
                    row.get("probability"),
                    row.get("severity"),
                    score,
                    level,
                    event_at,
                    event_at,
                    event_at,
                    row.get("step_updated_at"),
                ]
            )

        filename = f"risk-dashboard-{start.isoformat()}-{end.isoformat()}.csv"
        return Response(
            content=buffer.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Cache-Control": "no-store",
            },
        )

    base_key = make_cache_key(
        company_id=int(company_id),
        period=period,
        start=start.isoformat(),
        end=end.isoformat(),
        tz=tz,
        raw_requested=raw_requested,
        raw_effective=include_raw_effective,
        page=p,
        page_size=ps,
    )

    redis = get_redis_client()
    fresh_payload = await _redis_get(redis, _fresh_key(base_key))
    if fresh_payload:
        try:
            cached_payload = json.loads(fresh_payload)
            etag = compute_etag(cached_payload)
            if _etag_matches(request.headers.get("if-none-match"), etag):
                return Response(
                    status_code=304,
                    headers={
                        "ETag": etag,
                        "Cache-Control": CACHE_CONTROL_VALUE,
                        "X-Cache": "HIT-304",
                    },
                )
            return JSONResponse(
                content=cached_payload,
                headers={
                    "ETag": etag,
                    "Cache-Control": CACHE_CONTROL_VALUE,
                    "X-Cache": "HIT",
                },
            )
        except Exception:
            pass

    try:
        series_sql = text(SQL_SERIES_TEMPLATE.format(gran=granularity(period)))

        kpis_task = run_in_threadpool(_fetch_one, SQL_KPIS, params)
        risk_by_apr_task = run_in_threadpool(_fetch_all, SQL_RISK_BY_APR, params)
        series_task = run_in_threadpool(_fetch_all, series_sql, params)

        raw_count_task = None
        raw_data_task = None
        if include_raw_effective:
            raw_count_task = run_in_threadpool(_fetch_one, SQL_RAW_COUNT, params)
            raw_data_task = run_in_threadpool(
                _fetch_all,
                SQL_RAW_DATA,
                {**params, "limit": ps, "offset": offset},
            )

        results = await asyncio.gather(
            kpis_task,
            risk_by_apr_task,
            series_task,
            *(task for task in [raw_count_task, raw_data_task] if task is not None),
            return_exceptions=False,
        )
    except Exception:
        stale_payload = await _redis_get(redis, _stale_key(base_key))
        if stale_payload:
            try:
                stale = json.loads(stale_payload)
                etag = compute_etag(stale)
                if _etag_matches(request.headers.get("if-none-match"), etag):
                    return Response(
                        status_code=304,
                        headers={
                            "ETag": etag,
                            "Cache-Control": CACHE_CONTROL_VALUE,
                            "X-Cache": "STALE-304",
                            "X-Cache-Reason": "DB_ERROR_FALLBACK",
                        },
                    )
                return JSONResponse(
                    content=stale,
                    headers={
                        "ETag": etag,
                        "Cache-Control": CACHE_CONTROL_VALUE,
                        "X-Cache": "STALE",
                        "X-Cache-Reason": "DB_ERROR_FALLBACK",
                    },
                )
            except Exception:
                pass
        raise

    kpis_row = results[0] or {}
    risk_by_apr_rows = results[1] or []
    series_rows = results[2] or []

    raw_count_row = {}
    raw_rows = []
    if include_raw_effective:
        raw_count_row = results[3] or {}
        raw_rows = results[4] or []

    total_riscos = int(kpis_row.get("total_riscos", 0) or 0)
    aprs_monitoradas = int(kpis_row.get("aprs_monitoradas", 0) or 0)
    risco_baixo = int(kpis_row.get("risco_baixo", 0) or 0)
    risco_medio = int(kpis_row.get("risco_medio", 0) or 0)
    risco_alto = int(kpis_row.get("risco_alto_critico", 0) or 0)
    score_medio = float(kpis_row.get("score_medio") or 0)
    ultima_atualizacao = kpis_row.get("ultima_atualizacao")

    severity_distribution = [
        {"name": "Baixo", "key": "baixo", "value": risco_baixo, "color": COLORS["baixo"]},
        {"name": "Medio", "key": "medio", "value": risco_medio, "color": COLORS["medio"]},
        {"name": "Alto/Critico", "key": "alto", "value": risco_alto, "color": COLORS["alto"]},
    ]

    risk_by_apr = [
        {
            "aprId": row["apr_id"],
            "aprLabel": row["apr_label"],
            "baixo": row["baixo"],
            "medio": row["medio"],
            "alto": row["alto"],
            "total": row["total"],
        }
        for row in risk_by_apr_rows
    ]

    volume_over_time = [
        {
            "bucketStart": row["bucket"].date().isoformat()
            if isinstance(row["bucket"], datetime)
            else str(row["bucket"]),
            "bucketEnd": None,
            "baixo": row["baixo"],
            "medio": row["medio"],
            "alto": row["alto"],
            "total": row["total"],
        }
        for row in series_rows
    ]

    score_over_time = [
        {
            "bucketStart": row["bucket"].date().isoformat()
            if isinstance(row["bucket"], datetime)
            else str(row["bucket"]),
            "bucketEnd": None,
            "scoreMedio": float(row["score_medio"] or 0),
        }
        for row in series_rows
    ]

    payload: Dict[str, Any] = {
        "meta": {
            "period": period,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "timezone": tz,
            "generatedAt": generated_at,
            "classification": CLASSIFICATION,
            "timeSource": {
                "series": "risk_items.updated_at",
                "rawEventAt": "risk_items.updated_at",
                "stepContext": "passos.atualizado_em (opcional)",
            },
            "raw": {
                "requested": raw_requested,
                "included": include_raw_effective,
                "denied": bool(raw_requested and not raw_allowed),
                "deniedReason": (
                    None
                    if (not raw_requested or raw_allowed)
                    else "RBAC: role sem permissao para includeRaw"
                ),
            },
        },
        "kpis": {
            "aprsMonitoradas": aprs_monitoradas,
            "totalRiscos": total_riscos,
            "riscoBaixo": risco_baixo,
            "riscoMedio": risco_medio,
            "riscoAltoCritico": risco_alto,
            "scoreMedio": score_medio,
            "ultimaAtualizacao": ultima_atualizacao,
        },
        "charts": {
            "severityDistribution": severity_distribution,
            "riskByApr": risk_by_apr,
            "volumeOverTime": volume_over_time,
            "scoreOverTime": score_over_time,
        },
    }

    if include_raw_effective:
        total_rows = int(raw_count_row.get("total_rows", 0) or 0)
        total_pages = max(1, math.ceil(total_rows / ps)) if ps else 1
        payload["raw"] = {
            "pagination": {
                "page": p,
                "pageSize": ps,
                "totalRows": total_rows,
                "totalPages": total_pages,
            },
            "data": [
                {
                    "riskId": row["risk_id"],
                    "aprId": row["apr_id"],
                    "aprLabel": row["apr_label"],
                    "stepId": row["step_id"],
                    "hazardId": row["hazard_id"],
                    "riskDescription": row["risk_description"],
                    "probability": row["probability"],
                    "severity": row["severity"],
                    "score": int(row["score_final"]),
                    "riskLevel": _normalize_level(int(row["score_final"])),
                    "eventAt": row["event_at"],
                    "updatedAt": row["event_at"],
                    "stepUpdatedAt": row["step_updated_at"],
                }
                for row in raw_rows
            ],
        }

    encoded_payload = jsonable_encoder(payload)
    etag = compute_etag(encoded_payload)
    if _etag_matches(request.headers.get("if-none-match"), etag):
        return Response(
            status_code=304,
            headers={
                "ETag": etag,
                "Cache-Control": CACHE_CONTROL_VALUE,
                "X-Cache": "MISS-304",
            },
        )

    cache_state = "BYPASS"
    if redis is not None:
        payload_json = json.dumps(encoded_payload, ensure_ascii=False)
        await _redis_setex(redis, _fresh_key(base_key), CACHE_TTL_SECONDS, payload_json)
        await _redis_setex(
            redis, _stale_key(base_key), STALE_CACHE_TTL_SECONDS, payload_json
        )

        company_index = f"idx:cid={int(company_id)}"
        await _redis_sadd(redis, company_index, base_key)
        await _redis_expire(redis, company_index, 7 * 86400)

        for month in _month_keys_for_range(start, end):
            month_index = f"idx:cid={int(company_id)}:month={month}"
            await _redis_sadd(redis, month_index, base_key)
            await _redis_expire(redis, month_index, 30 * 86400)

        cache_state = "MISS"

    return JSONResponse(
        content=encoded_payload,
        headers={
            "ETag": etag,
            "Cache-Control": CACHE_CONTROL_VALUE,
            "X-Cache": cache_state,
        },
    )
