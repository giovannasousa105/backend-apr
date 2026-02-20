from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Iterable, List

logger = logging.getLogger(__name__)

_MOJIBAKE_MARKERS = (
    "\u00c3",  # ?
    "\u00c2",  # ?
    "\ufffd",  # ?
    "\u00e2\u20ac\u2122",  # ???
    "\u00e2\u20ac\u0153",  # ???
    "\u00e2\u20ac",        # ??
    "\u00e2\u20ac\u2013",  # ???
    "\u00e2\u20ac\u2014",  # ???
    "\u00e2\u20ac\u2026",  # ???
    "\u00e2\u20ac\u2018",  # ???
    "\u00c2\u00ba",        # ??
    "\u00c2\u00b0",        # ??
)

_MOJIBAKE_RE = re.compile("|".join(re.escape(m) for m in _MOJIBAKE_MARKERS))
_BAD_CHAR = "\ufffd"
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_EMPTY_SENTINELS = {"nan", "none", "null"}


def _mojibake_score(text: str) -> int:
    score = text.count(_BAD_CHAR)
    for marker in _MOJIBAKE_MARKERS:
        score += text.count(marker)
    return score


def _fix_mojibake(text: str) -> str:
    if not text or not _MOJIBAKE_RE.search(text):
        return text

    best = text
    best_score = _mojibake_score(text)

    for enc in ("latin-1", "cp1252"):
        try:
            candidate = text.encode(enc, errors="ignore").decode("utf-8", errors="ignore")
        except Exception:
            continue
        score = _mojibake_score(candidate)
        if score < best_score:
            best_score = score
            best = candidate

    return best


def _replace_bad_chars(text: str, origin: str | None, field: str | None) -> str:
    if _BAD_CHAR not in text:
        return text
    count = text.count(_BAD_CHAR)
    replaced = text.replace(_BAD_CHAR, "")
    logger.warning(
        "text_normalizer: replaced invalid char in %s (origin=%s, count=%s)",
        field or "unknown",
        origin or "unknown",
        count,
    )
    return replaced


def normalize_text(
    value: Any,
    *,
    keep_newlines: bool = True,
    origin: str | None = None,
    field: str | None = None,
) -> str | None:
    if value is None:
        return None

    text = str(value)
    if text == "":
        return ""
    if text.strip().lower() in _EMPTY_SENTINELS:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _fix_mojibake(text)
    text = unicodedata.normalize("NFKC", text)
    text = _CONTROL_CHARS.sub("", text)
    text = _replace_bad_chars(text, origin, field)

    if keep_newlines:
        lines = [re.sub(r"[ \t\u00A0]+", " ", line).strip() for line in text.split("\n")]
        collapsed: List[str] = []
        last_blank = False
        for line in lines:
            is_blank = line == ""
            if is_blank and last_blank:
                continue
            collapsed.append(line)
            last_blank = is_blank
        text = "\n".join(collapsed).strip()
    else:
        text = re.sub(r"[ \t\u00A0]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

    return _replace_bad_chars(text, origin, field)


def normalize_list(
    values: Iterable[Any] | None,
    *,
    origin: str | None = None,
    field: str | None = None,
) -> List[str]:
    if values is None:
        return []
    items: List[str] = []
    for item in values:
        normalized = normalize_text(item, origin=origin, field=field)
        if normalized is None:
            items.append("")
        else:
            items.append(normalized)
    return items
