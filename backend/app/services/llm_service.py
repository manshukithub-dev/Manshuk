from __future__ import annotations

import json
import logging
import os
from typing import Any
import httpx
from sqlalchemy.orm import Session

from backend.app.models import AppSetting
from backend.app.services.qa_engine import DetectedIssue

logger = logging.getLogger("qazaq_locqa.llm")


def mask_secret(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}{'*' * (len(secret) - 8)}{secret[-4:]}"


def get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.get(AppSetting, key)
    if row is not None and row.value != "":
        return row.value
    env_map = {
        "llm_provider": "LLM_PROVIDER",
        "llm_api_key": "LLM_API_KEY",
        "llm_model": "LLM_MODEL",
        "llm_base_url": "LLM_BASE_URL",
    }
    if key in env_map:
        return os.getenv(env_map[key], default)
    return default


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.get(AppSetting, key)
    if row is None:
        db.add(AppSetting(key=key, value=value))
    else:
        row.value = value


def enrich_issues_with_llm(
    issues: list[DetectedIssue],
    glossary: list[dict[str, Any]],
    provider: str,
    api_key: str,
    model: str,
    base_url: str = "",
    max_batch: int = 20,
) -> tuple[list[DetectedIssue], bool]:
    """
    Optionally refine suggestions for complex issues using Gemini or OpenAI-compatible LLM API.
    If no API key is configured or network fails, safely preserves rule-based output without logging secrets.
    Returns `(issues, llm_used)`.
    """
    if not api_key or not issues:
        return issues, False

    candidates = [iss for iss in issues if not iss.suggestion or iss.issue_type in ("untranslated", "wrong_language", "machine_translation_suspect")][:max_batch]
    if not candidates:
        return issues, True

    glossary_hint = ", ".join(f"{g['ru_term']} -> {g['kk_term']}" for g in glossary[:25])
    items_payload = [
        {
            "idx": idx,
            "lang": c.lang,
            "key": c.key,
            "issue_type": c.issue_type,
            "source_ru": c.source,
            "target": c.target,
        }
        for idx, c in enumerate(candidates)
    ]

    system_prompt = (
        "Сен мобильді ойындардың қазақша (kk) және өзбекше (uz) локализация сарапшысысың. "
        "Плейсхолдерлерді ({name}, {count}, %s) және ICU plural синтаксисін өзгертпе. "
        f"Глоссарий: {glossary_hint}. "
        "Тек JSON массивін қайтар: [{\"idx\": 0, \"suggestion\": \"...\"}]."
    )

    try:
        raw_reply = _call_provider(
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            system_prompt=system_prompt,
            user_prompt=json.dumps(items_payload, ensure_ascii=False),
        )
        cleaned = raw_reply.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            for entry in parsed:
                idx = entry.get("idx")
                sug = (entry.get("suggestion") or "").strip()
                if isinstance(idx, int) and 0 <= idx < len(candidates) and sug:
                    candidates[idx].suggestion = sug
        return issues, True
    except Exception as exc:
        # Never log API key or headers!
        logger.warning("LLM enrichment fallback to rule engine (%s)", type(exc).__name__)
        return issues, False


def test_llm_connection(provider: str, api_key: str, model: str, base_url: str = "") -> tuple[bool, str]:
    if not api_key:
        return False, "API кілті енгізілмеген. Ережелерге негізделген жергілікті QA қозғалтқышы белсенді."
    try:
        reply = _call_provider(
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            system_prompt="You are Qazaq Loc QA health check.",
            user_prompt="Тек 'OK' деп жауап бер.",
        )
        if reply:
            return True, f"AI провайдерімен ({provider} / {model}) байланыс сәтті орнатылды!"
        return False, "Бос жауап алынды."
    except Exception as exc:
        return False, f"AI провайдеріне қосылу мүмкін болмады ({type(exc).__name__}). Кілт пен модель атауын тексеріңіз."


def _call_provider(
    provider: str,
    api_key: str,
    model: str,
    base_url: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    prov = provider.lower().strip()
    with httpx.Client(timeout=18.0) as client:
        if prov == "gemini":
            mdl = model or "gemini-2.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{mdl}:generateContent"
            resp = client.post(
                url,
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json={
                    "systemInstruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                    "generationConfig": {"temperature": 0.2},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            endpoint = (base_url.rstrip("/") if base_url else "https://api.openai.com/v1") + "/chat/completions"
            resp = client.post(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model or "gpt-4o-mini",
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
