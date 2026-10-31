from __future__ import annotations

import re
from backend.app.services.kazakh_nlp import (
    KAZAKH_SPECIFIC_CHARS,
    LinguisticFinding,
    strip_placeholders_and_tags,
)

# Uzbek Latin characteristic markers (o', g', sh, ch, -ning, -ga, -dan, uchun, o'yin, ro'yxat, etc.)
UZBEK_LATIN_MARKERS_RE = re.compile(
    r"\b(uchun|bilan|va|yoki|o['ʻ’`]yin|o['ʻ’`]yinchi|ro['ʻ’`]yxat|xato|sotib|ijaraga|tugma|bekor|qilish|tasdiqlang|iltimos|mablag['ʻ’`]|yetarli|emas)\b|[oOgG]['ʻ’`]",
    re.IGNORECASE,
)

CYRILLIC_CHAR_RE = re.compile(r"[а-яА-ЯёЁәғқңөұүһіӘҒҚҢӨҰҮҺІ]")
LATIN_WORD_RE = re.compile(r"[a-zA-Z]{2,}")

# Broken Uzbek apostrophe patterns like o` or o' mixed with Cyrillic or wrong modifier
BROKEN_UZBEK_APOSTROPHE_RE = re.compile(r"\b([a-zA-Z]*[oOgG])`([a-zA-Z]+)\b")


def is_likely_uzbek_text(text: str) -> bool:
    cleaned = strip_placeholders_and_tags(text).strip()
    if not cleaned:
        return False
    if UZBEK_LATIN_MARKERS_RE.search(cleaned):
        return True
    has_latin = bool(LATIN_WORD_RE.search(cleaned))
    has_cyrillic = bool(CYRILLIC_CHAR_RE.search(cleaned))
    return has_latin and not has_cyrillic


def check_uzbek_localization(
    source_ru: str,
    target_uz: str,
    whitelisted_tokens: set[str] | None = None,
) -> list[LinguisticFinding]:
    r"""
    Validate Uzbek (`intl_uz.arb`) localization:
    - Detects Russian or Kazakh Cyrillic left inside Uzbek Latin localization (`wrong_language`).
    - Detects broken backtick apostrophes (`o\`` / `g\`` instead of standard Uzbek `oʻ` / `o'`).
    """
    findings: list[LinguisticFinding] = []
    whitelist = {w.lower() for w in (whitelisted_tokens or set())}
    cleaned = strip_placeholders_and_tags(target_uz).strip()
    if not cleaned:
        return findings

    # Check if Kazakh-specific letters appear in Uzbek translation
    if any(ch in KAZAKH_SPECIFIC_CHARS for ch in cleaned):
        findings.append(
            LinguisticFinding(
                issue_type="wrong_language",
                severity="high",
                evidence="Өзбекше локализация файлында (intl_uz.arb) қазақ әліпбиінің төл әріптері кездесті — қате тілде жазылған мәтін.",
                suggestion="",
                confidence=0.96,
                auto_fix_safe=False,
            )
        )
        return findings

    # Check if multi-letter Cyrillic words remain in Uzbek Latin target (excluding whitelisted slang/acronyms)
    cyr_words = re.findall(r"[а-яА-ЯёЁ]{2,}", cleaned)
    non_whitelisted_cyr = [w for w in cyr_words if w.lower() not in whitelist]
    if non_whitelisted_cyr and cleaned != strip_placeholders_and_tags(source_ru).strip():
        sample = ", ".join(f"«{w}»" for w in non_whitelisted_cyr[:3])
        findings.append(
            LinguisticFinding(
                issue_type="wrong_language",
                severity="high",
                evidence=(
                    f"Өзбекше (латын) аударма ішінде кирилл (орысша) сөздер қалып қойған: {sample}."
                ),
                suggestion="",
                confidence=0.93,
                auto_fix_safe=False,
            )
        )

    # Check Uzbek orthography: backtick ` used instead of standard apostrophe '/ʻ in o'/g'
    backtick_matches = BROKEN_UZBEK_APOSTROPHE_RE.findall(cleaned)
    if backtick_matches:
        fixed = re.sub(r"([oOgG])`", r"\1'", target_uz)
        findings.append(
            LinguisticFinding(
                issue_type="orthography",
                severity="low",
                evidence="Өзбек тіліндегі o'/g' әріптерінде гравис (`) таңбасы қолданылған; стандартты апостроф (') немесе (ʻ) ұсынылады.",
                suggestion=fixed,
                confidence=0.88,
                auto_fix_safe=True,
            )
        )

    return findings
