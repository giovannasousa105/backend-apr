from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import struct
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zlib
from typing import Any, Dict, List

from text_normalizer import normalize_text, normalize_list

logger = logging.getLogger(__name__)


class AIConfigError(RuntimeError):
    pass


class AIResponseError(RuntimeError):
    pass


class AITextInvalidEncodingError(RuntimeError):
    pass


def _sanitize_text(
    value: str | None,
    limit: int = 400,
    *,
    origin: str | None = None,
    field: str | None = None,
) -> str:
    normalized = normalize_text(value or "", keep_newlines=False, origin=origin, field=field) or ""
    return normalized[:limit]


def _normalize_list(value: List[str] | None, field: str) -> List[str]:
    if not value:
        return []
    return [v for v in normalize_list(value, origin="user", field=field) if v]


_GENERIC_TOKENS = {
    "naoinformado",
    "naoinformada",
    "naodefinido",
    "naodefinida",
    "indefinido",
    "indefinida",
    "desconhecido",
    "desconhecida",
    "naoaplicavel",
    "naoaplica",
    "adescrever",
    "tbd",
    "semdados",
    "seminformacao",
}
_NR_REFERENCE_RE = re.compile(r"\bNR\s*[-–]?\s*(\d{1,2})\b", re.IGNORECASE)

_QUOTA_RETRY_RE = re.compile(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", re.IGNORECASE)
_REPLACEMENT_CHAR = "\uFFFD"
_ENCODING_GUARD = (
    "IMPORTANTE: O JSON deve ser UTF-8 valido. "
    "Proibido incluir os caracteres de substituicao (U+FFFD) e mojibake "
    "(\\uFFFD, \\u00C3, \\u00C2). "
    "Se houver caracteres bugados, reescreva o texto com acentuacao correta."
)
_INVALID_ENCODING_MESSAGE = "Texto \u00ednv\u00e1lido retornado pela IA ap\u00f3s retries"


def _normalize_compare(text: str) -> str:
    if not text:
        return ""
    normalized = normalize_text(text, keep_newlines=False, origin="ai", field="compare") or ""
    normalized = unicodedata.normalize("NFKD", normalized)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[^a-zA-Z0-9]+", "", normalized).lower()
    return normalized


def _is_generic_text(text: str) -> bool:
    canonical = _normalize_compare(text)
    if not canonical:
        return True
    return canonical in _GENERIC_TOKENS


def _split_text_list(text: str, field: str) -> List[str]:
    if not text:
        return []
    parts = re.split(r"[;/,\n]+", text)
    items = []
    for part in parts:
        item = normalize_text(part, keep_newlines=False, origin="ai", field=field) or ""
        if item:
            items.append(item)
    return items


def _dedupe_list(items: List[str]) -> List[str]:
    seen: set[str] = set()
    deduped: List[str] = []
    for item in items:
        key = _normalize_compare(item)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _normalize_ai_list(value: Any, field: str, limit: int = 200) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = [
            normalize_text(item, keep_newlines=False, origin="ai", field=field) or ""
            for item in value
        ]
        items = [item for item in items if item]
    else:
        text = normalize_text(value, keep_newlines=False, origin="ai", field=field) or ""
        items = _split_text_list(text, field)

    items = [_sanitize_text(item, limit, origin="ai", field=field) for item in items if item]
    return _dedupe_list(items)


def _normalize_regulations(value: Any, field: str = "regulations") -> List[str]:
    items = _normalize_ai_list(value, field, limit=200)
    normalized: List[str] = []
    for item in items:
        parsed = _NR_REFERENCE_RE.sub(lambda match: f"NR-{int(match.group(1))}", item)
        parsed = _sanitize_text(parsed, 200, origin="ai", field=field)
        if parsed:
            normalized.append(parsed)
    return _dedupe_list(normalized)


def _iter_strings(obj: Any):
    if obj is None:
        return
    if isinstance(obj, str):
        yield obj
        return
    if isinstance(obj, dict):
        for value in obj.values():
            yield from _iter_strings(value)
        return
    if isinstance(obj, (list, tuple, set)):
        for value in obj:
            yield from _iter_strings(value)
        return


def _has_replacement_char(obj: Any) -> bool:
    for text in _iter_strings(obj):
        if _REPLACEMENT_CHAR in text:
            return True
    return False


def _reinforce_prompt(sys_prompt: str) -> str:
    if _ENCODING_GUARD in sys_prompt:
        return sys_prompt
    return f"{sys_prompt} {_ENCODING_GUARD}"


def _max_retries() -> int:
    try:
        retries = int(os.getenv("GEMINI_MAX_RETRIES", "3"))
    except Exception:
        retries = 3
    return max(1, retries)


def _retry_base_seconds() -> float:
    try:
        value = float(os.getenv("GEMINI_RETRY_BASE_SECONDS", "2"))
    except Exception:
        value = 2.0
    return max(1.0, min(value, 60.0))


def _retry_max_seconds() -> float:
    try:
        value = float(os.getenv("GEMINI_RETRY_MAX_SECONDS", "10"))
    except Exception:
        value = 10.0
    return max(1.0, min(value, 120.0))


def _fallback_enabled() -> bool:
    raw = (os.getenv("GEMINI_LOCAL_FALLBACK", "true") or "").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z0-9_-]*", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    return stripped


def _normalize_step(raw: Dict[str, Any]) -> Dict[str, str]:
    def pick(*keys: str) -> str:
        for key in keys:
            value = raw.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                items = _normalize_ai_list(value, key, limit=500)
                text = "; ".join(items)
            else:
                text = normalize_text(value, keep_newlines=False, origin="ai", field=key) or ""
            if text:
                return _sanitize_text(text, 500, origin="ai", field=key)
        return ""

    normas_list = _normalize_regulations(
        raw.get("normas")
        or raw.get("norma")
        or raw.get("nrs")
        or raw.get("nr")
        or raw.get("regulations")
        or raw.get("regulation")
        or raw.get("references")
        or raw.get("referencias"),
        "normas",
    )
    if not normas_list:
        normas_list = _normalize_regulations(
            pick("normas", "norma", "nrs", "nr", "regulations", "references"),
            "normas",
        )

    return {
        "passo": pick("passo", "step", "descricao", "description"),
        "perigo": pick("perigo", "hazard", "hazards"),
        "consequencia": pick("consequencia", "risco", "riscos", "risk", "risks"),
        "salvaguarda": pick("salvaguarda", "medida", "medidas", "measure", "measures"),
        "epi": pick("epi", "epis", "ppe"),
        "normas": "; ".join(normas_list),
    }


def _build_prompt(
    atividade: str,
    descricao: str,
    ferramentas: List[str],
    energias: List[str],
    contexto: Dict[str, Any],
    max_steps: int,
) -> tuple[str, str]:
    sys_prompt = (
        "Voce e um engenheiro de seguranca do trabalho. "
        "Gere um passo a passo de APR em portugues (pt-BR). "
        "Aplique todas as NR (Normas Regulamentadoras brasileiras) pertinentes à atividade, "
        "seguindo controles obrigatorios, hierarquia de protecao, bloqueio/etiquetagem quando houver energia "
        "e requisitos de EPI/EPC conforme NR-06, NR-10, NR-12, NR-18, NR-33, NR-35 etc. "
        "Responda SOMENTE com JSON valido no formato: "
        '{"passos":[{"passo":"","perigo":"","consequencia":"","salvaguarda":"","epi":"","normas":""}]} '
        "Regras: 1 a %d passos; cada campo deve ter pelo menos um item; "
        "use ';' para separar multiplos itens; "
        "o campo normas deve listar as NRs usadas no passo (ex.: NR-35; NR-06); "
        "sem markdown; sem listas numeradas."
    ) % max_steps

    linhas = [
        f"Atividade: {atividade or 'nao informado'}",
        f"Descricao: {descricao or 'nao informado'}",
        f"Ferramentas: {', '.join(ferramentas) if ferramentas else 'nao informado'}",
        f"Energias: {', '.join(energias) if energias else 'nao informado'}",
    ]
    if contexto:
        for key, value in contexto.items():
            if value:
                linhas.append(f"{key}: {value}")

    linhas.append("Responda em JSON valido.")
    user_input = "\n".join(linhas)
    return sys_prompt, user_input


def _build_image_steps_prompt(
    descricao: str,
    max_steps: int,
    *,
    use_image: bool,
    activity_context: Dict[str, Any] | None = None,
    normative_context: Dict[str, Any] | None = None,
) -> tuple[str, str]:
    activity_context = activity_context or {}
    normative_context = normative_context or {}
    sys_prompt = (
        "Voce e um engenheiro de seguranca do trabalho. "
        "Gere um passo a passo tecnico em portugues (pt-BR). "
        "Use exclusivamente a imagem anexada quando houver imagem, "
        "ou somente a descricao quando nao houver imagem. "
        "Nao invente situacoes nao compativeis com a fonte. "
        "Aplique todas as NR (Normas Regulamentadoras brasileiras) pertinentes à atividade, "
        "seguindo controles obrigatorios, hierarquia de protecao, bloqueio/etiquetagem quando houver energia "
        "e requisitos de EPI/EPC conforme NR-06, NR-10, NR-12, NR-18, NR-33, NR-35 etc. "
        "Considere conhecimento tecnico padrao e normas aplicaveis quando evidentes. "
        "Responda SOMENTE com JSON valido no formato: "
        '{"steps":[{"step_order":1,"description":"","hazard":"","consequences":"","safeguards":"","epis":[],"regulations":[]}]} '
        "Regras: 1 a %d passos; step_order sequencial; "
        "cada campo deve ser preenchido com informacao tecnica objetiva; "
        "nenhum campo pode ser vazio, generico ou repetido; "
        "description = o que esta sendo feito; "
        "hazard = situacao perigosa; "
        "consequences = o que pode ocorrer se falhar; "
        "safeguards = medidas preventivas; "
        "epis = lista de EPIs especificos; "
        "regulations = lista de NRs aplicadas no passo (ex.: NR-35, NR-06); "
        "sem markdown; sem listas numeradas; sem emojis; sem metaforas."
    ) % max_steps

    active_frameworks = [
        str(item).strip()
        for item in (normative_context.get("active_frameworks") or [])
        if str(item).strip()
    ]
    if active_frameworks:
        sys_prompt += (
            " Priorize explicitamente os frameworks normativos ativos fornecidos pelo contexto "
            "e inclua essas referencias no campo regulations."
        )

    lines = []
    if use_image:
        lines.append("Fonte principal: imagem anexada.")
    else:
        lines.append(
            f"Fonte principal: descricao da atividade: {descricao or 'nao informado'}"
        )

    if normative_context:
        base_framework = normalize_text(
            normative_context.get("base_framework_id"),
            keep_newlines=False,
            origin="system",
            field="base_framework_id",
        ) or "NR_BR"
        optional_frameworks = [
            str(item).strip()
            for item in (normative_context.get("optional_framework_ids") or [])
            if str(item).strip()
        ]
        if optional_frameworks:
            lines.append(
                f"Normas ativas: base={base_framework}; opcionais={', '.join(optional_frameworks)}."
            )
        else:
            lines.append(f"Normas ativas: base={base_framework}; opcionais=nenhuma.")
        mode = normalize_text(
            normative_context.get("risk_engine_mode"),
            keep_newlines=False,
            origin="system",
            field="risk_engine_mode",
        )
        if mode:
            lines.append(f"Modo do motor de risco: {mode}.")

    if activity_context:
        activity_name = normalize_text(
            activity_context.get("activity_name"),
            keep_newlines=False,
            origin="excel",
            field="activity_name",
        )
        activity_id = normalize_text(
            activity_context.get("activity_id"),
            keep_newlines=False,
            origin="excel",
            field="activity_id",
        )
        if activity_name or activity_id:
            lines.append(
                f"Atividade de referencia do Excel: {activity_name or 'n/a'} (ID: {activity_id or 'n/a'})."
            )

        excel_steps = [
            _sanitize_text(step, 220, origin="excel", field="excel_steps")
            for step in (activity_context.get("step_descriptions") or [])
            if _sanitize_text(step, 220, origin="excel", field="excel_steps")
        ]
        if excel_steps:
            lines.append(
                "Passos de referencia (Excel): " + " | ".join(excel_steps[:4]) + "."
            )

        excel_hazards = _normalize_ai_list(
            activity_context.get("hazards"),
            "excel_hazards",
            limit=120,
        )
        if excel_hazards:
            lines.append(
                "Perigos de referencia (Excel): " + "; ".join(excel_hazards[:8]) + "."
            )

        excel_measures = _normalize_ai_list(
            activity_context.get("measures"),
            "excel_measures",
            limit=120,
        )
        if excel_measures:
            lines.append(
                "Salvaguardas de referencia (Excel): "
                + "; ".join(excel_measures[:8])
                + "."
            )

        excel_regs = _normalize_regulations(
            activity_context.get("regulations"),
            "excel_regulations",
        )
        if excel_regs:
            lines.append(
                "Regulacoes de referencia (Excel): " + "; ".join(excel_regs[:10]) + "."
            )

    lines.append("Responda em JSON valido.")
    user_input = "\n".join(lines)
    return sys_prompt, user_input


def _normalize_structured_step(raw: Dict[str, Any]) -> Dict[str, Any]:
    def pick_text(limit: int, *keys: str) -> str:
        for key in keys:
            value = raw.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                text = "; ".join([v for v in normalize_list(value, origin="ai", field=key) if v])
            else:
                text = normalize_text(value, keep_newlines=False, origin="ai", field=key) or ""
            if text:
                return _sanitize_text(text, limit, origin="ai", field=key)
        return ""

    epis = _normalize_ai_list(raw.get("epis"), "epis")
    if not epis:
        epis = _normalize_ai_list(raw.get("epi"), "epis")
    if not epis:
        epis = _normalize_ai_list(raw.get("ppe"), "epis")
    regulations = _normalize_regulations(raw.get("regulations"), "regulations")
    if not regulations:
        regulations = _normalize_regulations(raw.get("normas"), "regulations")
    if not regulations:
        regulations = _normalize_regulations(raw.get("nrs"), "regulations")
    if not regulations:
        regulations = _normalize_regulations(raw.get("nr"), "regulations")

    return {
        "step_order": 0,
        "description": pick_text(800, "description", "descricao", "passo", "step"),
        "hazard": pick_text(600, "hazard", "perigo", "hazards"),
        "consequences": pick_text(600, "consequences", "consequencia", "consequencias", "riscos", "risks"),
        "safeguards": pick_text(600, "safeguards", "salvaguarda", "salvaguardas", "medidas", "medidas_controle", "controls"),
        "epis": epis,
        "regulations": regulations,
    }


def _validate_structured_step(step: Dict[str, Any], index: int) -> None:
    fields = ["description", "hazard", "consequences", "safeguards"]
    for field in fields:
        value = step.get(field) or ""
        if _is_generic_text(value):
            raise AIResponseError(f"Campo {field} vazio ou generico no passo {index}")

    epis = step.get("epis") or []
    if not isinstance(epis, list) or not epis:
        raise AIResponseError(f"Campo epis vazio no passo {index}")
    for epi in epis:
        if _is_generic_text(str(epi)):
            raise AIResponseError(f"EPI generico no passo {index}")

    regulations = step.get("regulations") or []
    if not isinstance(regulations, list) or not regulations:
        raise AIResponseError(f"Campo regulations vazio no passo {index}")
    for regulation in regulations:
        if _is_generic_text(str(regulation)):
            raise AIResponseError(f"Regulacao generica no passo {index}")

    canonical = {field: _normalize_compare(step.get(field) or "") for field in fields}
    if len(set(canonical.values())) != len(canonical):
        raise AIResponseError(f"Campos duplicados no passo {index}")


def _parse_error_message(body: str) -> str:
    try:
        data = json.loads(body)
        if isinstance(data, dict):
            err = data.get("error") or {}
            msg = err.get("message") or data.get("message")
            if msg:
                return str(msg)
    except Exception:
        pass
    return body.strip()


def _sanitize_api_key(raw: str | None) -> str:
    if not raw:
        return ""
    return raw.strip().strip('"').strip("'").strip()


def _candidate_api_keys() -> List[tuple[str, str]]:
    seen: set[str] = set()
    candidates: List[tuple[str, str]] = []

    for env_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        key = _sanitize_api_key(os.getenv(env_name))
        if not key or key in seen:
            continue
        seen.add(key)
        candidates.append((env_name, key))

    return candidates


def _is_api_key_error(message: str) -> bool:
    msg = (message or "").lower()
    return (
        "api key not found" in msg
        or "api key invalid" in msg
        or "api_key_invalid" in msg
        or "api_key_service_blocked" in msg
    )


def _is_quota_or_rate_limited(message: str) -> bool:
    msg = (message or "").lower()
    return (
        "quota exceeded" in msg
        or "rate limit" in msg
        or "resource has been exhausted" in msg
        or "too many requests" in msg
    )


def _quota_retry_seconds(message: str, attempt: int) -> float | None:
    if not _is_quota_or_rate_limited(message):
        return None

    match = _QUOTA_RETRY_RE.search(message or "")
    if match:
        try:
            value = float(match.group(1))
        except Exception:
            value = _retry_base_seconds() * (2 ** max(0, attempt - 1))
    else:
        value = _retry_base_seconds() * (2 ** max(0, attempt - 1))

    return max(1.0, min(value, _retry_max_seconds()))


def _has_any_term(text: str, terms: List[str]) -> bool:
    lower = (text or "").lower()
    return any(term in lower for term in terms)


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for item in items:
        value = _sanitize_text(item, 200, origin="ai", field="fallback")
        if not value:
            continue
        key = _normalize_compare(value)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _fallback_regulations(context_text: str, energias: List[str]) -> List[str]:
    regs = ["NR-01", "NR-06", "NR-12"]
    if _has_any_term(context_text, ["altura", "andaime", "telhado", "escada", "linha de vida"]):
        regs.extend(["NR-35", "NR-18"])
    if _has_any_term(context_text, ["eletric", "painel", "choque", "energiz"]):
        regs.append("NR-10")
    if _has_any_term(context_text, ["solda", "oxicorte", "arco", "quente", "esmerilh"]):
        regs.extend(["NR-18", "NR-12"])
    if _has_any_term(context_text, ["confinad", "atmosfera", "gases", "ventilacao"]):
        regs.append("NR-33")
    if _has_any_term(context_text, ["guindaste", "icamento", "içamento", "talha", "carga suspensa"]):
        regs.append("NR-11")
    if _has_any_term(context_text, ["escav", "vala", "trincheira"]):
        regs.append("NR-18")

    energias_text = " ".join(energias).lower()
    if "eletric" in energias_text:
        regs.append("NR-10")
    if any(term in energias_text for term in ["mecanic", "hidraul", "pneumat", "residual", "cinetic"]):
        regs.append("NR-12")

    return _dedupe_keep_order(regs)


def _fallback_epis(context_text: str) -> List[str]:
    epis = ["Capacete", "Oculos de protecao", "Luvas", "Botina de seguranca"]
    if _has_any_term(context_text, ["altura", "andaime", "telhado", "escada"]):
        epis.extend(["Cinto paraquedista", "Talabarte duplo"])
    if _has_any_term(context_text, ["solda", "oxicorte", "esmerilh", "ruido"]):
        epis.extend(["Protetor auricular", "Protetor facial"])
    if _has_any_term(context_text, ["eletric", "painel", "energiz"]):
        epis.extend(["Luva isolante", "Vestimenta antichama"])
    return _dedupe_keep_order(epis)


def _fallback_main_hazard(context_text: str) -> tuple[str, str, str]:
    if _has_any_term(context_text, ["altura", "andaime", "telhado", "escada", "linha de vida"]):
        return (
            "Queda de altura e queda de materiais",
            "Lesoes graves, fraturas, obito e danos a terceiros",
            "Linha de vida certificada; ancoragem aprovada; isolamento de area inferior; check-list pre-uso",
        )
    if _has_any_term(context_text, ["eletric", "painel", "choque", "energiz"]):
        return (
            "Contato com partes energizadas e arco eletrico",
            "Queimaduras graves, choque eletrico e parada cardiorrespiratoria",
            "Bloqueio e etiquetagem (LOTO); teste de ausencia de tensao; ferramentas isoladas",
        )
    if _has_any_term(context_text, ["solda", "oxicorte", "esmerilh", "quente"]):
        return (
            "Projecao de particulas, queimaduras e principio de incendio",
            "Lesoes oculares, queimaduras e incendio local",
            "Barreira contra fagulhas; extintor disponivel; limpeza de inflamaveis; autorizacao para trabalho a quente",
        )
    return (
        "Esmagamento, corte e colisao com partes moveis",
        "Lesoes graves, afastamento e dano material",
        "Protetores fisicos instalados; distancia segura; operador habilitado e comunicacao ativa",
    )


def _build_local_fallback_structured_steps(
    *,
    atividade: str,
    descricao: str,
    ferramentas: List[str],
    energias: List[str],
    max_steps: int,
    use_image: bool,
) -> List[Dict[str, Any]]:
    context_text = " ".join([atividade, descricao, " ".join(ferramentas), " ".join(energias)]).lower()
    regulations = _fallback_regulations(context_text, energias)
    epis = _fallback_epis(context_text)
    hazard, consequences, safeguards = _fallback_main_hazard(context_text)

    activity_label = _sanitize_text(
        atividade or ("Atividade observada em evidencia tecnica" if use_image else "Atividade operacional"),
        180,
        origin="ai",
        field="fallback_activity",
    )

    base_steps: List[Dict[str, Any]] = [
        {
            "description": f"Planejar e liberar frente de trabalho para {activity_label}",
            "hazard": "Inicio sem permissao, isolamento incompleto e falha de comunicacao",
            "consequences": "Acidente com trabalhadores e terceiros, retrabalho e atraso operacional",
            "safeguards": "DDS inicial; permissao de trabalho valida; isolamento e sinalizacao da area; definicao de responsaveis",
            "epis": epis,
            "regulations": regulations,
        },
        {
            "description": "Inspecionar ferramentas, equipamentos e energias perigosas antes do inicio",
            "hazard": "Partida inesperada, falha mecanica, ferramenta inadequada ou energia residual",
            "consequences": "Choque eletrico, esmagamento, cortes e danos ao equipamento",
            "safeguards": "Check-list pre-uso; bloqueio e etiquetagem quando aplicavel; teste funcional e liberacao formal",
            "epis": epis,
            "regulations": regulations,
        },
        {
            "description": f"Executar {activity_label} com controle operacional continuo",
            "hazard": hazard,
            "consequences": consequences,
            "safeguards": safeguards,
            "epis": epis,
            "regulations": regulations,
        },
        {
            "description": "Encerrar atividade com liberacao segura da area e registro tecnico",
            "hazard": "Retorno indevido de energia, liberacao prematura e falha na comunicacao final",
            "consequences": "Acidente na retomada, reincidencia de risco e perda de rastreabilidade",
            "safeguards": "Conferencia final; retirada controlada de bloqueios; liberacao da area pelo responsavel; registro de evidencias",
            "epis": epis,
            "regulations": regulations,
        },
        {
            "description": "Registrar licoes aprendidas e atualizar plano preventivo da APR",
            "hazard": "Repeticao de desvios por ausencia de padronizacao",
            "consequences": "Aumento de ocorrencias e nao conformidades em auditoria",
            "safeguards": "Atualizacao de procedimentos; treinamento de reforco; revisao periodica dos controles",
            "epis": epis,
            "regulations": regulations,
        },
    ]

    limited = base_steps[: max(1, min(max_steps, len(base_steps)))]
    normalized: List[Dict[str, Any]] = []
    for index, step in enumerate(limited, start=1):
        normalized.append(
            {
                "step_order": index,
                "description": _sanitize_text(step["description"], 800, origin="ai", field="description"),
                "hazard": _sanitize_text(step["hazard"], 600, origin="ai", field="hazard"),
                "consequences": _sanitize_text(step["consequences"], 600, origin="ai", field="consequences"),
                "safeguards": _sanitize_text(step["safeguards"], 600, origin="ai", field="safeguards"),
                "epis": _dedupe_keep_order(step["epis"]),
                "regulations": _dedupe_keep_order(step["regulations"]),
            }
        )
    return normalized


def _fallback_text_steps(
    *,
    atividade: str,
    descricao: str,
    ferramentas: List[str],
    energias: List[str],
    max_steps: int,
    reason: str,
) -> Dict[str, Any]:
    steps = _build_local_fallback_structured_steps(
        atividade=atividade,
        descricao=descricao,
        ferramentas=ferramentas,
        energias=energias,
        max_steps=max_steps,
        use_image=False,
    )
    legacy_steps = [
        {
            "passo": item["description"],
            "perigo": item["hazard"],
            "consequencia": item["consequences"],
            "salvaguarda": item["safeguards"],
            "epi": "; ".join(item["epis"]),
            "normas": "; ".join(item["regulations"]),
        }
        for item in steps
    ]
    logger.warning("Usando fallback local de IA (texto). Motivo: %s", reason)
    return {"passos": legacy_steps, "source": "fallback_local"}


def _fallback_image_steps(
    *,
    descricao: str,
    max_steps: int,
    reason: str,
    use_image: bool,
) -> Dict[str, Any]:
    steps = _build_local_fallback_structured_steps(
        atividade="Atividade de campo",
        descricao=descricao,
        ferramentas=[],
        energias=[],
        max_steps=max_steps,
        use_image=use_image,
    )
    logger.warning("Usando fallback local de IA (imagem). Motivo: %s", reason)
    return {"steps": steps, "source": "fallback_local"}


def _build_gemini_url(base_url: str, model: str, api_key: str) -> str:
    endpoint = f"{base_url}/models/{model}:generateContent"
    query = urllib.parse.urlencode({"key": api_key})
    separator = "&" if "?" in endpoint else "?"
    return f"{endpoint}{separator}{query}"


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
    return struct.pack("!I", len(payload)) + chunk_type + payload + struct.pack("!I", crc)


def _build_placeholder_png(prompt: str, width: int = 960, height: int = 540) -> bytes:
    width = max(320, min(1280, int(width)))
    height = max(180, min(1024, int(height)))
    digest = hashlib.sha256((prompt or "hcs-ai-image").encode("utf-8")).digest()
    base_r = 20 + (digest[0] % 50)
    base_g = 70 + (digest[1] % 90)
    base_b = 120 + (digest[2] % 100)

    raw = bytearray()
    x_den = max(1, width - 1)
    y_den = max(1, height - 1)
    for y in range(height):
        raw.append(0)
        y_mix = y / y_den
        for x in range(width):
            x_mix = x / x_den
            r = min(255, int(base_r + 50 * x_mix))
            g = min(255, int(base_g + 40 * y_mix))
            b = min(255, int(base_b + 35 * (1.0 - x_mix * 0.5)))
            raw.extend((r, g, b))

    ihdr = struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(bytes(raw), level=6)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", idat)
        + _png_chunk(b"IEND", b"")
    )


def _build_step_image_prompt(
    *,
    activity: str,
    step_description: str,
    hazards: str,
    consequences: str,
    safeguards: str,
    epis: str,
    regulations: str,
) -> str:
    return (
        "Ilustracao tecnica realista de seguranca do trabalho, ambiente industrial, luz natural, "
        "estilo corporativo, sem marcas, sem texto na imagem. "
        f"Atividade: {activity or 'Operacao de campo'}. "
        f"Passo: {step_description or 'Execucao segura da atividade'}. "
        f"Perigos: {hazards or 'Risco operacional'}. "
        f"Consequencias: {consequences or 'Lesoes e danos materiais'}. "
        f"Salvaguardas: {safeguards or 'Controles preventivos e EPC/EPI'}. "
        f"EPIs: {epis or 'Capacete, oculos, luvas, botina'}. "
        f"Normas: {regulations or 'NR aplicaveis'}."
    )


def generate_ai_step_image(
    *,
    activity: str | None,
    step_description: str | None,
    hazards: str | None,
    consequences: str | None,
    safeguards: str | None,
    epis: str | None,
    regulations: str | None,
) -> Dict[str, Any]:
    prompt = _build_step_image_prompt(
        activity=_sanitize_text(activity or "", 200, origin="ai", field="activity"),
        step_description=_sanitize_text(step_description or "", 400, origin="ai", field="step_description"),
        hazards=_sanitize_text(hazards or "", 300, origin="ai", field="hazards"),
        consequences=_sanitize_text(consequences or "", 300, origin="ai", field="consequences"),
        safeguards=_sanitize_text(safeguards or "", 300, origin="ai", field="safeguards"),
        epis=_sanitize_text(epis or "", 300, origin="ai", field="epis"),
        regulations=_sanitize_text(regulations or "", 200, origin="ai", field="regulations"),
    )

    model = (os.getenv("AI_IMAGE_MODEL", "flux") or "flux").strip()
    base_url = (
        os.getenv("AI_IMAGE_API_URL", "https://image.pollinations.ai/prompt")
        or "https://image.pollinations.ai/prompt"
    ).strip().rstrip("/")
    timeout = float(os.getenv("AI_IMAGE_TIMEOUT", "35"))
    width = max(320, min(1280, int(os.getenv("AI_IMAGE_WIDTH", "1024"))))
    height = max(180, min(1024, int(os.getenv("AI_IMAGE_HEIGHT", "768"))))

    encoded_prompt = urllib.parse.quote(prompt, safe="")
    url = (
        f"{base_url}/{encoded_prompt}"
        f"?model={urllib.parse.quote(model, safe='')}"
        f"&width={width}&height={height}&nologo=true&safe=true"
    )
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "image/png,image/jpeg;q=0.9,*/*;q=0.8",
            "User-Agent": "HCS-Apr/1.0",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            image_bytes = resp.read()
            content_type = (resp.headers.get("Content-Type") or "").lower()
            if not image_bytes:
                raise AIResponseError("Imagem de IA vazia")
            mime = "image/png" if "png" in content_type else "image/jpeg"
            return {"bytes": image_bytes, "mime": mime, "source": "ai_provider"}
    except Exception as exc:
        logger.warning("Falha ao gerar imagem via provedor de IA. Usando fallback local. Erro: %s", exc)
        return {
            "bytes": _build_placeholder_png(prompt, width=width, height=height),
            "mime": "image/png",
            "source": "fallback_local",
        }


def _call_gemini(payload: Dict[str, Any]) -> Dict[str, Any]:
    key_candidates = _candidate_api_keys()
    if not key_candidates:
        raise AIConfigError("GEMINI_API_KEY/GOOGLE_API_KEY nao configurada")

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    base_url = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta")
    data = json.dumps(payload).encode("utf-8")
    timeout = float(os.getenv("GEMINI_TIMEOUT", "30"))
    last_api_key_error: AIResponseError | None = None

    for key_source, api_key in key_candidates:
        url = _build_gemini_url(base_url, model, api_key)
        headers = {
            "Content-Type": "application/json",
            # Mantido para compatibilidade; a key principal vai na query string.
            "x-goog-api-key": api_key,
        }
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            parsed = _parse_error_message(detail) or f"Gemini HTTP {exc.code}"
            logger.error("Gemini HTTP %s (%s): %s", exc.code, key_source, detail)

            if _is_api_key_error(parsed):
                last_api_key_error = AIResponseError(parsed)
                logger.warning("Gemini rejeitou chave de %s; tentando proxima chave", key_source)
                continue

            raise AIResponseError(parsed) from exc
        except urllib.error.URLError as exc:
            logger.error("Gemini connection error (%s): %s", key_source, exc)
            raise AIResponseError("Gemini connection error") from exc

    if last_api_key_error:
        logger.error("Todas as chaves Gemini foram rejeitadas: %s", last_api_key_error)
        raise AIConfigError("Servico de IA indisponivel: chave da API invalida ou ausente")

    raise AIResponseError("Falha ao autenticar no Gemini")


def _extract_gemini_text(payload: Dict[str, Any]) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        return ""
    content = (candidates[0] or {}).get("content") or {}
    parts = content.get("parts") or []
    for part in parts:
        text = part.get("text")
        if text:
            return str(text).strip()
    return ""


def _call_gemini_with_fallback(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return _call_gemini(payload)
    except AIResponseError as exc:
        msg = str(exc)
        if "responseMimeType" in msg or "mimeType" in msg or "not supported" in msg:
            payload = dict(payload)
            gen = dict(payload.get("generationConfig") or {})
            gen.pop("responseMimeType", None)
            payload["generationConfig"] = gen
            return _call_gemini(payload)
        raise


def generate_ai_steps(
    *,
    atividade: str,
    descricao: str,
    ferramentas: List[str] | None = None,
    energias: List[str] | None = None,
    contexto: Dict[str, Any] | None = None,
    max_steps: int = 6,
) -> Dict[str, Any]:
    ferramentas = _normalize_list(ferramentas, "ferramentas")
    energias = _normalize_list(energias, "energias")
    contexto = contexto or {}

    max_steps = max(1, min(int(max_steps), 12))

    sys_prompt, user_input = _build_prompt(
        _sanitize_text(atividade, 200, origin="user", field="atividade"),
        _sanitize_text(descricao, 600, origin="user", field="descricao"),
        ferramentas,
        energias,
        contexto,
        max_steps,
    )

    fallback_reason: str | None = None
    retries = _max_retries()
    for attempt in range(1, retries + 1):
        try:
            current_prompt = sys_prompt if attempt == 1 else _reinforce_prompt(sys_prompt)
            payload = {
                "system_instruction": {
                    "parts": [{"text": current_prompt}],
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": user_input}],
                    }
                ],
                "generationConfig": {
                    "temperature": 0.3,
                    "responseMimeType": "application/json",
                },
            }

            response = _call_gemini_with_fallback(payload)
            output_text = _extract_gemini_text(response)
            if not output_text:
                raise AIResponseError("Gemini sem output_text")

            output_text = _strip_code_fences(output_text)
            try:
                data = json.loads(output_text)
            except json.JSONDecodeError as exc:
                logger.warning("Falha ao decodificar JSON da Gemini (tentativa %s/%s)", attempt, retries)
                raise AIResponseError("JSON invalido da Gemini") from exc

            steps = data.get("passos") or data.get("steps") or []
            if not isinstance(steps, list):
                raise AIResponseError("Formato inesperado de passos")
            global_normas = _normalize_regulations(
                data.get("normas")
                or data.get("nrs")
                or data.get("nr")
                or data.get("regulations")
                or data.get("references"),
                "normas",
            )

            normalized: List[Dict[str, str]] = []
            for item in steps:
                if not isinstance(item, dict):
                    continue
                step = _normalize_step(item)
                if not step["passo"]:
                    continue
                if not step.get("normas") and global_normas:
                    step["normas"] = "; ".join(global_normas)
                normalized.append(step)

            if not normalized:
                raise AIResponseError("Nenhum passo gerado pela Gemini")

            has_invalid_char = _has_replacement_char(data) or _has_replacement_char(normalized)
            if has_invalid_char:
                logger.warning("IA retornou texto com U+FFFD (tentativa %s/%s)", attempt, retries)
                if attempt >= retries:
                    if _fallback_enabled():
                        fallback_reason = _INVALID_ENCODING_MESSAGE
                        break
                    raise AITextInvalidEncodingError(_INVALID_ENCODING_MESSAGE)
                continue

            return {"passos": normalized[:max_steps], "source": "gemini"}
        except AIConfigError as exc:
            if _fallback_enabled():
                fallback_reason = str(exc)
                break
            raise
        except AIResponseError as exc:
            fallback_reason = str(exc)
            wait_seconds = _quota_retry_seconds(str(exc), attempt)
            if wait_seconds and attempt < retries:
                logger.warning(
                    "Quota da IA atingida (tentativa %s/%s). Aguardando %.1fs antes de tentar novamente.",
                    attempt,
                    retries,
                    wait_seconds,
                )
                time.sleep(wait_seconds)
                continue
            if attempt >= retries:
                if _fallback_enabled():
                    break
                raise
            logger.warning("IA tentativa %s/%s falhou: %s", attempt, retries, exc)
            continue

    if _fallback_enabled():
        return _fallback_text_steps(
            atividade=atividade,
            descricao=descricao,
            ferramentas=ferramentas,
            energias=energias,
            max_steps=max_steps,
            reason=fallback_reason or "falha_desconhecida",
        )
    raise AIResponseError(fallback_reason or "Falha ao gerar passos com IA")


def generate_ai_steps_from_image(
    *,
    image_bytes: bytes | None,
    image_mime: str | None,
    descricao: str | None,
    max_steps: int = 6,
    activity_context: Dict[str, Any] | None = None,
    normative_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    max_steps = max(1, min(int(max_steps), 12))
    use_image = bool(image_bytes)

    if not use_image:
        descricao = _sanitize_text(descricao or "", 800, origin="user", field="descricao")
        if not descricao:
            raise AIResponseError("Descricao nao informada")

    sys_prompt, user_input = _build_image_steps_prompt(
        descricao or "",
        max_steps,
        use_image=use_image,
        activity_context=activity_context,
        normative_context=normative_context,
    )

    parts: List[Dict[str, Any]] = [{"text": user_input}]
    if use_image:
        mime = image_mime or "image/jpeg"
        if not mime.startswith("image/"):
            mime = "image/jpeg"
        data = base64.b64encode(image_bytes).decode("ascii")
        parts.append(
            {
                "inlineData": {
                    "mimeType": mime,
                    "data": data,
                }
            }
        )

    retries = _max_retries()
    fallback_reason: str | None = None
    for attempt in range(1, retries + 1):
        try:
            current_prompt = sys_prompt if attempt == 1 else _reinforce_prompt(sys_prompt)
            payload = {
                "system_instruction": {"parts": [{"text": current_prompt}]},
                "contents": [
                    {
                        "role": "user",
                        "parts": parts,
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json",
                },
            }

            response = _call_gemini_with_fallback(payload)
            output_text = _extract_gemini_text(response)
            if not output_text:
                raise AIResponseError("Gemini sem output_text")

            output_text = _strip_code_fences(output_text)
            try:
                data = json.loads(output_text)
            except json.JSONDecodeError as exc:
                logger.warning("Falha ao decodificar JSON da Gemini (tentativa %s/%s)", attempt, retries)
                raise AIResponseError("JSON invalido da Gemini") from exc

            steps = data.get("steps") or data.get("passos") or []
            if not isinstance(steps, list):
                raise AIResponseError("Formato inesperado de steps")
            global_regulations = _normalize_regulations(
                data.get("regulations")
                or data.get("normas")
                or data.get("nrs")
                or data.get("nr"),
                "regulations",
            )

            normalized: List[Dict[str, Any]] = []
            for item in steps:
                if not isinstance(item, dict):
                    continue
                step = _normalize_structured_step(item)
                if not step.get("regulations") and global_regulations:
                    step["regulations"] = global_regulations
                step["step_order"] = len(normalized) + 1
                _validate_structured_step(step, step["step_order"])
                normalized.append(step)
                if len(normalized) >= max_steps:
                    break

            if not normalized:
                raise AIResponseError("Nenhum passo gerado pela Gemini")

            has_invalid_char = _has_replacement_char(data) or _has_replacement_char(normalized)
            if has_invalid_char:
                logger.warning("IA retornou texto com U+FFFD (tentativa %s/%s)", attempt, retries)
                if attempt >= retries:
                    if _fallback_enabled():
                        fallback_reason = _INVALID_ENCODING_MESSAGE
                        break
                    raise AITextInvalidEncodingError(_INVALID_ENCODING_MESSAGE)
                continue

            return {"steps": normalized}
        except AIConfigError as exc:
            if _fallback_enabled():
                fallback_reason = str(exc)
                break
            raise
        except AIResponseError as exc:
            fallback_reason = str(exc)
            wait_seconds = _quota_retry_seconds(str(exc), attempt)
            if wait_seconds and attempt < retries:
                logger.warning(
                    "Quota da IA (imagem) atingida (tentativa %s/%s). Aguardando %.1fs antes de tentar novamente.",
                    attempt,
                    retries,
                    wait_seconds,
                )
                time.sleep(wait_seconds)
                continue
            if attempt >= retries:
                if _fallback_enabled():
                    break
                raise
            logger.warning("IA imagem tentativa %s/%s falhou: %s", attempt, retries, exc)
            continue

    if _fallback_enabled():
        return _fallback_image_steps(
            descricao=descricao or "",
            max_steps=max_steps,
            reason=fallback_reason or "falha_desconhecida",
            use_image=use_image,
        )
    raise AIResponseError(fallback_reason or "Falha ao gerar passos com IA")
