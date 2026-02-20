from __future__ import annotations

import base64
import json
import logging
import os
import re
import unicodedata
import urllib.error
import urllib.request
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

    return {
        "passo": pick("passo", "step", "descricao", "description"),
        "perigo": pick("perigo", "hazard", "hazards"),
        "consequencia": pick("consequencia", "risco", "riscos", "risk", "risks"),
        "salvaguarda": pick("salvaguarda", "medida", "medidas", "measure", "measures"),
        "epi": pick("epi", "epis", "ppe"),
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
        '{"passos":[{"passo":"","perigo":"","consequencia":"","salvaguarda":"","epi":""}]} '
        "Regras: 1 a %d passos; cada campo deve ter pelo menos um item; "
        "use ';' para separar multiplos itens; sem markdown; sem listas numeradas."
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
) -> tuple[str, str]:
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
        '{"steps":[{"step_order":1,"description":"","hazard":"","consequences":"","safeguards":"","epis":[]}]} '
        "Regras: 1 a %d passos; step_order sequencial; "
        "cada campo deve ser preenchido com informacao tecnica objetiva; "
        "nenhum campo pode ser vazio, generico ou repetido; "
        "description = o que esta sendo feito; "
        "hazard = situacao perigosa; "
        "consequences = o que pode ocorrer se falhar; "
        "safeguards = medidas preventivas; "
        "epis = lista de EPIs especificos; "
        "sem markdown; sem listas numeradas; sem emojis; sem metaforas."
    ) % max_steps

    if use_image:
        user_input = "Fonte: imagem anexada. Analise somente a imagem."
    else:
        user_input = f"Descricao da atividade: {descricao or 'nao informado'}"
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

    return {
        "step_order": 0,
        "description": pick_text(800, "description", "descricao", "passo", "step"),
        "hazard": pick_text(600, "hazard", "perigo", "hazards"),
        "consequences": pick_text(600, "consequences", "consequencia", "consequencias", "riscos", "risks"),
        "safeguards": pick_text(600, "safeguards", "salvaguarda", "salvaguardas", "medidas", "medidas_controle", "controls"),
        "epis": epis,
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


def _call_gemini(payload: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise AIConfigError("GEMINI_API_KEY nao configurada")

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    base_url = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta")
    url = f"{base_url}/models/{model}:generateContent"

    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    timeout = float(os.getenv("GEMINI_TIMEOUT", "30"))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        logger.error("Gemini HTTP %s: %s", exc.code, detail)
        raise AIResponseError(_parse_error_message(detail) or f"Gemini HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        logger.error("Gemini connection error: %s", exc)
        raise AIResponseError("Gemini connection error") from exc


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

    retries = _max_retries()
    for attempt in range(1, retries + 1):
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
            logger.error("Falha ao decodificar JSON da Gemini: %s", output_text[:500])
            raise AIResponseError("JSON invalido da Gemini") from exc

        steps = data.get("passos") or data.get("steps") or []
        if not isinstance(steps, list):
            raise AIResponseError("Formato inesperado de passos")

        normalized: List[Dict[str, str]] = []
        for item in steps:
            if not isinstance(item, dict):
                continue
            step = _normalize_step(item)
            if not step["passo"]:
                continue
            normalized.append(step)

        if not normalized:
            raise AIResponseError("Nenhum passo gerado pela Gemini")

        has_invalid_char = _has_replacement_char(data) or _has_replacement_char(normalized)
        if has_invalid_char:
            logger.warning("IA retornou texto com U+FFFD (tentativa %s/%s)", attempt, retries)
            if attempt >= retries:
                raise AITextInvalidEncodingError(_INVALID_ENCODING_MESSAGE)
            continue

        return {"passos": normalized[:max_steps], "source": "gemini"}


def generate_ai_steps_from_image(
    *,
    image_bytes: bytes | None,
    image_mime: str | None,
    descricao: str | None,
    max_steps: int = 6,
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
    for attempt in range(1, retries + 1):
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
            logger.error("Falha ao decodificar JSON da Gemini: %s", output_text[:500])
            raise AIResponseError("JSON invalido da Gemini") from exc

        steps = data.get("steps") or data.get("passos") or []
        if not isinstance(steps, list):
            raise AIResponseError("Formato inesperado de steps")

        normalized: List[Dict[str, Any]] = []
        for item in steps:
            if not isinstance(item, dict):
                continue
            step = _normalize_structured_step(item)
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
                raise AITextInvalidEncodingError(_INVALID_ENCODING_MESSAGE)
            continue

        return {"steps": normalized}
