from __future__ import annotations

import re
from typing import Any, Literal

ResponseLanguage = Literal["es", "en", "pt-BR"]
ReelsMetricsStatus = Literal["available", "unavailable"]

_WORD_PATTERN = re.compile(r"[a-záéíóúüñãõâêôàç']+")
_SPANISH_HINTS = {
    "a",
    "al",
    "audiencia",
    "campana",
    "campaña",
    "con",
    "confianza",
    "creador",
    "de",
    "del",
    "el",
    "en",
    "estrategia",
    "la",
    "las",
    "los",
    "marca",
    "necesito",
    "para",
    "por",
    "que",
    "quiero",
    "reputacion",
    "reputación",
    "sin",
    "una",
    "un",
    "y",
}
_PORTUGUESE_HINTS = {
    "campanha",
    "com",
    "confianca",
    "confiança",
    "conteudo",
    "conteúdo",
    "criador",
    "estrategia",
    "estratégia",
    "fortalecer",
    "nao",
    "não",
    "objetivo",
    "para",
    "preciso",
    "quero",
    "reputacao",
    "reputação",
    "sem",
    "uma",
    "voces",
    "vocês",
    "voce",
    "você",
}
_ENGLISH_HINTS = {
    "a",
    "and",
    "audience",
    "brand",
    "campaign",
    "community",
    "creator",
    "for",
    "goal",
    "need",
    "of",
    "on",
    "strategy",
    "the",
    "to",
    "trust",
    "want",
    "with",
}


def normalize_response_language(value: Any) -> ResponseLanguage | None:
    if value is None:
        return None

    normalized = str(value).strip().lower()
    if normalized.startswith("es"):
        return "es"
    if normalized.startswith("en"):
        return "en"
    if normalized.startswith("pt"):
        return "pt-BR"
    return None


def infer_response_language(
    *texts: Any,
    default: ResponseLanguage = "es",
) -> ResponseLanguage:
    content = " ".join(str(text) for text in texts if text is not None).strip().lower()
    if not content:
        return default

    tokens = _WORD_PATTERN.findall(content)
    if not tokens:
        return default

    spanish_score = sum(token in _SPANISH_HINTS for token in tokens)
    portuguese_score = sum(token in _PORTUGUESE_HINTS for token in tokens)
    english_score = sum(token in _ENGLISH_HINTS for token in tokens)

    if re.search(r"[áéíóúüñ¿¡]", content):
        spanish_score += 2
    if re.search(r"[ãõç]", content):
        portuguese_score += 2
    if re.search(r"\b\w+ción\b|\b\w+ciones\b", content):
        spanish_score += 2
    if re.search(r"\b\w+ção\b|\b\w+ções\b", content):
        portuguese_score += 2

    if portuguese_score > spanish_score and portuguese_score > english_score:
        return "pt-BR"
    if spanish_score > english_score:
        return "es"
    if english_score > spanish_score and english_score > portuguese_score:
        return "en"
    return default


def normalize_reels_metrics_status(
    value: Any,
    default: ReelsMetricsStatus = "unavailable",
) -> ReelsMetricsStatus:
    normalized = str(value).strip().lower() if value is not None else default
    if normalized == "available":
        return "available"
    return "unavailable"


__all__ = [
    "ResponseLanguage",
    "ReelsMetricsStatus",
    "infer_response_language",
    "normalize_reels_metrics_status",
    "normalize_response_language",
]
