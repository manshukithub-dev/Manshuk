from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from backend.app.services.arb_parser import extract_html_tags, extract_icu_structure
from backend.app.services.kazakh_nlp import (
    KAZAKH_SPECIFIC_CHARS,
    RUSSIAN_ONLY_CYRILLIC,
    check_kazakh_orthography,
    check_kazakh_suffix_harmony,
    strip_placeholders_and_tags,
    transliterate_kk_to_latin,
)
from backend.app.services.uzbek_nlp import check_uzbek_localization

# Whitelisted gaming brands, acronyms, nicknames, and universal tokens that should NOT be flagged
DEFAULT_BRAND_AND_SLANG_WHITELIST = {
    "grand coins",
    "grand",
    "grand mobile",
    "grand rp mobile",
    "rp",
    "vip",
    "id",
    "gps",
    "fps",
    "ping",
    "afk",
    "dm",
    "db",
    "mg",
    "tk",
    "sk",
    "pg",
    "rk",
    "discord",
    "telegram",
    "youtube",
    "tiktok",
    "instagram",
    "ok",
    "pin",
    "sms",
    "cvv",
    "atm",
    "npc",
    "xp",
    "hp",
    "mp",
    "pvp",
    "гк",
    "варн",
    "мут",
    "фура",
    "фракция",
    "бизнес",
    "гараж",
    "тюнинг",
    "дрифт",
    "промокод",
    "донат",
    "квест",
    "скин",
    "кейс",
    "ранг",
    "слот",
    "чат",
    "банк",
    "казино",
    "паспорт",
    "лицензия",
}

UI_COMPACT_KEY_RE = re.compile(
    r"(?:^|_)(button|btn|tab|nav|badge|label|cta|chip|menu_item|short)(?:_|$)",
    re.IGNORECASE,
)

VERBOSE_BUTTON_FILLER_KK_RE = re.compile(
    r"\s+(үшін\s+басыңыз|түймесін\s+басыңыз|батырмасын\s+басыңыз)\s*[.!]*$",
    re.IGNORECASE,
)
VERBOSE_BUTTON_FILLER_UZ_RE = re.compile(
    r"\s+(uchun\s+bosing|tugmasini\s+bosing)\s*[.!]*$",
    re.IGNORECASE,
)

# Machine translation literal calques in Kazakh / Uzbek
MT_SUSPECT_PATTERNS_KK: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"үлкен\s+монета(?:лар)?", re.IGNORECASE),
        "«Grand Coins» бренд атауы сөзбе-сөз машиналық түрде «Үлкен монеталар» деп аударылған.",
        "Grand Coins",
    ),
    (
        re.compile(r"\bсіз\s+сіздің\b|\bсіздің\s+сіз\b", re.IGNORECASE),
        "Машиналық аудармаға тән есімдіктердің қайталануы («сіз сіздің»).",
        "",
    ),
    (
        re.compile(r"\bқабылдау\s+душ\b|\bжасау\s+скриншот\b", re.IGNORECASE),
        "Орыс тіліндегі сөз тәртібімен тікелей калька жасалған машиналық тіркес.",
        "",
    ),
    (
        re.compile(r"\bсіз\s+сенімдісіз\s+бе\s+не\b", re.IGNORECASE),
        "«Вы уверены что...» құрылымының сапасыз машиналық калькасы.",
        "Сіз шынымен растайсыз ба?",
    ),
    (
        re.compile(r"\bбасыңыз\s+үшін\b|\bүшін\s+түймесін\s+басыңыз\s+ойнау\b", re.IGNORECASE),
        "Қазақ тілінің сөйлем құрылымы (етістік сөйлем соңында тұруы тиіс) бұзылған машиналық аударма.",
        "",
    ),
]

MT_SUSPECT_PATTERNS_UZ: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"katta\s+tangalar", re.IGNORECASE),
        "«Grand Coins» валютасы машиналық аударма арқылы «Katta tangalar» деп қате аударылған.",
        "Grand Coins",
    ),
    (
        re.compile(r"\bsiz\s+ishonchingiz\s+komilmi\s+nima\b", re.IGNORECASE),
        "Орысша сөйлем құрылымынан сөзбе-сөз аударылған табиғи емес тіркес.",
        "Ishonchingiz komilmi?",
    ),
]

# Russian function words & endings strongly indicating untranslated/wrong-language Russian sentence
RUSSIAN_GRAMMAR_WORDS_RE = re.compile(
    r"\b(вы|ваш|ваша|ваше|ваши|пожалуйста|недостаточно|нажмите|откройте|закрыть|купить|получить|игрок|игрока|уровень|ошибка|доступно|недоступно|отмена|подтвердите|выберите|введите|успешно|отправлено|подарок|средств|только|или|для|после|перед)\b",
    re.IGNORECASE,
)

ENGLISH_WORDS_RE = re.compile(
    r"\b(please|click|button|cancel|confirm|player|insufficient|funds|loading|error|warning|welcome|buy|rent|select|family|fraction)\b",
    re.IGNORECASE,
)

PURE_NON_ALPHA_RE = re.compile(r"^[\d\s\W_]+$", re.UNICODE)
NICKNAME_OR_CODE_RE = re.compile(r"^(?:@[a-zA-Z0-9_]+|[A-Z0-9_-]{2,12}|https?://\S+)$")


@dataclass
class DetectedIssue:
    key: str
    lang: str
    issue_type: str
    severity: str  # high, medium, low
    source: str
    target: str
    evidence: str
    suggestion: str
    confidence: float
    auto_fix_safe: bool = True


@dataclass
class EngineConfig:
    length_overflow_ratio: float = 1.45
    button_max_chars: int = 24
    latin_check_enabled: bool = True


def _ru_stem(term: str) -> str:
    """Create a conservative stem for Russian inflected form matching."""
    t = term.strip().lower()
    if " " in t or len(t) <= 3:
        return t
    if t.endswith(("ия", "ья")):
        return t[:-2]
    if t.endswith(("ать", "ять", "ить")):
        return t[:-3]
    if t.endswith(("а", "я", "ы", "и", "у", "ю", "е", "о")):
        return t[:-1]
    return t


def _target_stem(term: str) -> str:
    t = term.strip().lower()
    if len(t) <= 3:
        return t
    return t


def _is_exempt_passthrough(text: str, whitelist: set[str]) -> bool:
    cleaned = strip_placeholders_and_tags(text).strip()
    if not cleaned:
        return True
    if PURE_NON_ALPHA_RE.match(cleaned):
        return True
    if NICKNAME_OR_CODE_RE.match(cleaned):
        return True
    if cleaned.lower() in whitelist:
        return True
    # Check if every word in the string is whitelisted or numeric
    tokens = re.findall(r"[a-zA-Zа-яА-ЯёЁәғқңөұүһіӘҒҚҢӨҰҮҺІ']+", cleaned)
    if tokens and all(tok.lower() in whitelist for tok in tokens):
        return True
    return False


def _concise_button_suggestion(key: str, source: str, target: str, lang: str, glossary: list[dict[str, Any]]) -> str:
    # 1. Check if source matches a glossary entry directly
    src_norm = source.strip().lower()
    for g in glossary:
        if g["ru_term"].strip().lower() == src_norm:
            cand = g.get("uz_term") if lang == "uz" else g.get("kk_term")
            if cand:
                return cand[:1].upper() + cand[1:] if source[:1].isupper() else cand

    # 2. Strip verbose "үшін басыңыз" / "uchun bosing" button filler
    if lang == "kk":
        trimmed = VERBOSE_BUTTON_FILLER_KK_RE.sub("", target).strip()
        if trimmed and trimmed != target:
            return trimmed[:1].upper() + trimmed[1:]
    else:
        trimmed = VERBOSE_BUTTON_FILLER_UZ_RE.sub("", target).strip()
        if trimmed and trimmed != target:
            return trimmed[:1].upper() + trimmed[1:]

    # 3. Common concise mobile game UI button dictionary
    common_ru_buttons = {
        "арендовать": ("Жалға алу", "Ijaraga olish"),
        "купить": ("Сатып алу", "Sotib olish"),
        "продать": ("Сату", "Sotish"),
        "отмена": ("Бас тарту", "Bekor qilish"),
        "закрыть": ("Жабу", "Yopish"),
        "войти": ("Кіру", "Kirish"),
        "выйти": ("Шығу", "Chiqish"),
        "сохранить": ("Сақтау", "Saqlash"),
        "принять": ("Қабылдау", "Qabul qilish"),
        "отправить": ("Жіберу", "Yuborish"),
        "далее": ("Келесі", "Keyingi"),
        "назад": ("Артқа", "Orqaga"),
    }
    if src_norm in common_ru_buttons:
        kk_btn, uz_btn = common_ru_buttons[src_norm]
        return uz_btn if lang == "uz" else kk_btn

    return target


def run_qa_checks(
    source_entries: dict[str, str],
    target_entries: dict[str, str],
    lang: str = "kk",
    glossary: list[dict[str, Any]] | None = None,
    config: EngineConfig | None = None,
) -> list[DetectedIssue]:
    """
    Execute all 12 QA localization issue detectors across `source_entries` (Russian)
    and `target_entries` (Kazakh `kk` or Uzbek `uz`).
    Designed for O(N) scalability on 5,500+ keys.
    """
    cfg = config or EngineConfig()
    glossary_list = glossary or []
    issues: list[DetectedIssue] = []

    # Build whitelist from defaults + glossary terms
    whitelist = set(DEFAULT_BRAND_AND_SLANG_WHITELIST)
    for g in glossary_list:
        if g.get("is_slang_or_brand") or g["ru_term"].strip().lower() == g["kk_term"].strip().lower():
            whitelist.add(g["ru_term"].strip().lower())
            whitelist.add(g["kk_term"].strip().lower())
            if g.get("uz_term"):
                whitelist.add(g["uz_term"].strip().lower())
        if g.get("en_term"):
            whitelist.add(g["en_term"].strip().lower())

    # Pre-compile glossary stems for fast lookup
    compiled_glossary: list[tuple[dict[str, Any], re.Pattern[str], str]] = []
    for g in glossary_list:
        ru_t = g["ru_term"].strip()
        target_t = (g.get("uz_term") or g["kk_term"]).strip() if lang == "uz" else g["kk_term"].strip()
        if not ru_t or not target_t:
            continue
        stem = _ru_stem(ru_t)
        if len(ru_t) <= 3 and ru_t.isupper():
            pat = re.compile(rf"\b{re.escape(ru_t)}\b")
        else:
            pat = re.compile(rf"\b{re.escape(stem)}[а-яА-ЯёЁ]*\b", re.IGNORECASE)
        compiled_glossary.append((g, pat, _target_stem(target_t)))

    # Pre-compute consistency map for `inconsistent_term` (Rule 8)
    # Group non-empty normalized source -> Counter of target translations
    source_to_targets: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for key, src_val in source_entries.items():
        tgt_val = (target_entries.get(key) or "").strip()
        src_clean = src_val.strip()
        if len(src_clean) >= 3 and tgt_val and src_clean.lower() != tgt_val.lower():
            source_to_targets[src_clean].append((key, tgt_val))

    inconsistent_keys: dict[str, tuple[str, list[str]]] = {}
    for src_clean, pairs in source_to_targets.items():
        distinct_targets = Counter(t for _, t in pairs)
        if len(distinct_targets) > 1:
            canonical_target, _ = distinct_targets.most_common(1)[0]
            variants = list(distinct_targets.keys())
            for k, t in pairs:
                if t != canonical_target:
                    inconsistent_keys[k] = (canonical_target, variants)

    # Main O(N) pass over all source keys
    for key, src in source_entries.items():
        raw_tgt = target_entries.get(key)

        # 1. untranslated
        if raw_tgt is None or not raw_tgt.strip() or raw_tgt.strip().upper() in {"TODO", "TBD", "UNTRANSLATED"}:
            suggestion = _concise_button_suggestion(key, src, "", lang, glossary_list)
            issues.append(
                DetectedIssue(
                    key=key,
                    lang=lang,
                    issue_type="untranslated",
                    severity="high",
                    source=src,
                    target=raw_tgt or "",
                    evidence="Аударма жолы бос немесе мақсатты ARB файлында бұл кілт мүлде жоқ.",
                    suggestion=suggestion if suggestion else "",
                    confidence=0.99,
                    auto_fix_safe=bool(suggestion),
                )
            )
            continue

        tgt = raw_tgt

        # Extract ICU placeholders & plural/select structure once per entry
        src_ph, src_icu, _ = extract_icu_structure(src)
        tgt_ph, tgt_icu, tgt_icu_errors = extract_icu_structure(tgt)

        # 4. plural_mismatch (ICU syntax & plural/select parity)
        if tgt_icu_errors or (src_icu and not tgt_icu):
            if tgt_icu_errors:
                ev = "ICU көпше/таңдау құрылымы бұзылған: " + "; ".join(tgt_icu_errors[:2])
            else:
                ev = (
                    f"Түпнұсқада ICU «{src_icu[0].kind}» ({src_icu[0].variable}) құрылымы бар, "
                    f"ал аудармада ICU көпше/таңдау құрылымы жоғалған."
                )
            # Build safe ICU plural template suggestion if source had plural
            plural_sug = ""
            if src_icu and src_icu[0].kind == "plural":
                var_n = src_icu[0].variable
                other_Sample = tgt.strip() or f"{{{var_n}}}"
                if f"{{{var_n}}}" not in other_Sample:
                    other_Sample = f"{{{var_n}}} {other_Sample}"
                plural_sug = f"{{{var_n}, plural, one{{{other_Sample}}} other{{{other_Sample}}}}}"
            issues.append(
                DetectedIssue(
                    key=key,
                    lang=lang,
                    issue_type="plural_mismatch",
                    severity="high",
                    source=src,
                    target=tgt,
                    evidence=ev,
                    suggestion=plural_sug,
                    confidence=0.97,
                    auto_fix_safe=False,
                )
            )

        # 3. placeholder_mismatch
        if src_ph != tgt_ph:
            missing_ph = sorted(src_ph - tgt_ph)
            extra_ph = sorted(tgt_ph - src_ph)
            parts_ev: list[str] = []
            if missing_ph:
                parts_ev.append("жетіспейді: " + ", ".join(f"{{{p}}}" if not p.startswith(("%", "$")) else p for p in missing_ph))
            if extra_ph:
                parts_ev.append("артық/өзгертілген: " + ", ".join(f"{{{p}}}" if not p.startswith(("%", "$")) else p for p in extra_ph))
            ph_sug = tgt
            # If exactly 1 placeholder was renamed (e.g. {aty} instead of {name}), fix it cleanly!
            if len(missing_ph) == 1 and len(extra_ph) == 1 and not missing_ph[0].startswith(("%", "$")) and not extra_ph[0].startswith(("%", "$")):
                ph_sug = tgt.replace(f"{{{extra_ph[0]}}}", f"{{{missing_ph[0]}}}")
            elif missing_ph and not extra_ph:
                appended = " ".join(f"{{{p}}}" if not p.startswith(("%", "$")) else p for p in missing_ph)
                ph_sug = f"{tgt.rstrip()} {appended}".strip()

            issues.append(
                DetectedIssue(
                    key=key,
                    lang=lang,
                    issue_type="placeholder_mismatch",
                    severity="high",
                    source=src,
                    target=tgt,
                    evidence=f"Плейсхолдерлер түпнұсқамен сәйкес келмейді ({'; '.join(parts_ev)}).",
                    suggestion=ph_sug if ph_sug != tgt else "",
                    confidence=0.99,
                    auto_fix_safe=(len(missing_ph) == 1 and len(extra_ph) == 1),
                )
            )

        # 2. same_as_source
        if src.strip().lower() == tgt.strip().lower() and not _is_exempt_passthrough(src, whitelist):
            sug = _concise_button_suggestion(key, src, "", lang, glossary_list)
            issues.append(
                DetectedIssue(
                    key=key,
                    lang=lang,
                    issue_type="same_as_source",
                    severity="high",
                    source=src,
                    target=tgt,
                    evidence="Аударма мәтіні орысша түпнұсқамен бірдей күйінде қалған.",
                    suggestion=sug if sug != tgt else "",
                    confidence=0.98,
                    auto_fix_safe=bool(sug and sug != tgt),
                )
            )
            # Skip downstream linguistic checks since string is identical to Russian source
            continue

        # 11. wrong_language
        tgt_clean = strip_placeholders_and_tags(tgt).strip()
        if lang == "kk" and tgt_clean and not _is_exempt_passthrough(tgt, whitelist):
            has_kk_chars = any(ch in KAZAKH_SPECIFIC_CHARS for ch in tgt_clean)
            has_ru_only_chars = any(ch in RUSSIAN_ONLY_CYRILLIC for ch in tgt_clean)
            ru_grammar_hits = RUSSIAN_GRAMMAR_WORDS_RE.findall(tgt_clean)
            en_hits = [w for w in ENGLISH_WORDS_RE.findall(tgt_clean) if w.lower() not in whitelist]
            uz_markers = re.findall(r"\b(uchun|o['ʻ’`]yin|o['ʻ’`]yinchi|ro['ʻ’`]yxat|sotib|ijaraga|tugma)\b", tgt_clean, re.IGNORECASE)

            if uz_markers:
                issues.append(
                    DetectedIssue(
                        key=key,
                        lang=lang,
                        issue_type="wrong_language",
                        severity="high",
                        source=src,
                        target=tgt,
                        evidence=f"Қазақша файлда өзбек тіліндегі сөздер табылды ({', '.join(uz_markers[:2])}).",
                        suggestion="",
                        confidence=0.95,
                        auto_fix_safe=False,
                    )
                )
            elif en_hits and not any("\u0400" <= ch <= "\u04ff" for ch in tgt_clean):
                issues.append(
                    DetectedIssue(
                        key=key,
                        lang=lang,
                        issue_type="wrong_language",
                        severity="high",
                        source=src,
                        target=tgt,
                        evidence=f"Қазақша аударма орнына ағылшынша мәтін жазылған ({', '.join(en_hits[:3])}).",
                        suggestion=_concise_button_suggestion(key, src, "", lang, glossary_list),
                        confidence=0.96,
                        auto_fix_safe=False,
                    )
                )
            elif not has_kk_chars and (len(ru_grammar_hits) >= 1 or has_ru_only_chars):
                non_wl_ru = [w for w in ru_grammar_hits if w.lower() not in whitelist]
                if non_wl_ru or has_ru_only_chars:
                    issues.append(
                        DetectedIssue(
                            key=key,
                            lang=lang,
                            issue_type="wrong_language",
                            severity="high",
                            source=src,
                            target=tgt,
                            evidence="Мақсатты жол қазақ тілінде емес, орыс тілінде жазылған.",
                            suggestion=_concise_button_suggestion(key, src, "", lang, glossary_list),
                            confidence=0.94,
                            auto_fix_safe=False,
                        )
                    )

        # Uzbek wrong_language + Uzbek orthography
        if lang == "uz":
            for uz_finding in check_uzbek_localization(src, tgt, whitelist):
                issues.append(
                    DetectedIssue(
                        key=key,
                        lang=lang,
                        issue_type=uz_finding.issue_type,
                        severity=uz_finding.severity,
                        source=src,
                        target=tgt,
                        evidence=uz_finding.evidence,
                        suggestion=uz_finding.suggestion,
                        confidence=uz_finding.confidence,
                        auto_fix_safe=uz_finding.auto_fix_safe,
                    )
                )

        # 5. glossary_violation
        tgt_lower = tgt.lower()
        for g_item, ru_pat, expected_stem in compiled_glossary:
            if ru_pat.search(src):
                expected_term = (g_item.get("uz_term") or g_item["kk_term"]) if lang == "uz" else g_item["kk_term"]
                if expected_stem not in tgt_lower and expected_term.lower() not in tgt_lower:
                    # Craft smart replacement suggestion for common glossary violations
                    sug_gloss = tgt
                    wrong_synonyms = {
                        "семья": ["жанұя", "семья", "әулет"],
                        "grand coins": ["үлкен монеталар", "гранд коинс", "гранд тиындар", "katta tangalar"],
                        "фракция": ["топ", "ұйым", "партия"],
                        "фура": ["жүк көлігі", "трактор"],
                        "мут": ["дыбыссыз", "үндемеу"],
                        "варн": ["ескерту жаза"],
                    }
                    ru_k = g_item["ru_term"].strip().lower()
                    for syn in wrong_synonyms.get(ru_k, []):
                        syn_re = re.compile(re.escape(syn), re.IGNORECASE)
                        if syn_re.search(sug_gloss):
                            sug_gloss = syn_re.sub(expected_term, sug_gloss, count=1)
                            break
                    if sug_gloss == tgt and src.strip().lower() == ru_k:
                        sug_gloss = expected_term

                    issues.append(
                        DetectedIssue(
                            key=key,
                            lang=lang,
                            issue_type="glossary_violation",
                            severity="high" if g_item.get("is_slang_or_brand") else "medium",
                            source=src,
                            target=tgt,
                            evidence=(
                                f"Глоссарий талабы бұзылған: «{g_item['ru_term']}» термині "
                                f"«{expected_term}» ретінде қолданылуы тиіс."
                            ),
                            suggestion=sug_gloss if sug_gloss != tgt else expected_term,
                            confidence=0.94,
                            auto_fix_safe=(sug_gloss != tgt),
                        )
                    )

        # 6. length_overflow (Cyrillic + Official Kazakh Latin length check)
        src_vis = strip_placeholders_and_tags(src).strip()
        tgt_vis = strip_placeholders_and_tags(tgt).strip()
        is_ui_control = bool(UI_COMPACT_KEY_RE.search(key)) or (0 < len(src_vis) <= 16 and " " not in src_vis)
        ratio = (len(tgt_vis) / max(len(src_vis), 1)) if src_vis else 1.0

        latin_vis = transliterate_kk_to_latin(tgt_vis) if (lang == "kk" and cfg.latin_check_enabled) else tgt_vis
        effective_len = max(len(tgt_vis), len(latin_vis))

        if is_ui_control and len(src_vis) >= 4 and (effective_len > cfg.button_max_chars or ratio > 1.75):
            concise = _concise_button_suggestion(key, src, tgt, lang, glossary_list)
            latin_note = (
                f" (латын әліпбиінде: {len(latin_vis)} таңба)"
                if lang == "kk" and len(latin_vis) > len(tgt_vis)
                else ""
            )
            issues.append(
                DetectedIssue(
                    key=key,
                    lang=lang,
                    issue_type="length_overflow",
                    severity="high",
                    source=src,
                    target=tgt,
                    evidence=(
                        f"Түпнұсқамен салыстырғанда интерфейс мәтіні тым ұзын "
                        f"({len(src_vis)} → {len(tgt_vis)} таңба, {ratio:.1f}x){latin_note}."
                    ),
                    suggestion=concise if concise != tgt else "",
                    confidence=0.95,
                    auto_fix_safe=bool(concise and concise != tgt and len(concise) < len(tgt)),
                )
            )
        elif len(src_vis) >= 12 and ratio > cfg.length_overflow_ratio and len(tgt_vis) - len(src_vis) >= 14:
            concise = _concise_button_suggestion(key, src, tgt, lang, glossary_list)
            issues.append(
                DetectedIssue(
                    key=key,
                    lang=lang,
                    issue_type="length_overflow",
                    severity="medium",
                    source=src,
                    target=tgt,
                    evidence=(
                        f"Аударма мәтіні түпнұсқадан едәуір ұзын ({len(src_vis)} → {len(tgt_vis)} таңба, {ratio:.2f}x); "
                        f"мобильді экранда мәтін қиылып қалуы мүмкін."
                    ),
                    suggestion=concise if concise != tgt else "",
                    confidence=0.86,
                    auto_fix_safe=False,
                )
            )

        # 7. machine_translation_suspect
        mt_patterns = MT_SUSPECT_PATTERNS_KK if lang == "kk" else MT_SUSPECT_PATTERNS_UZ
        for pat, reason, fixed_phrase in mt_patterns:
            if pat.search(tgt):
                mt_sug = pat.sub(fixed_phrase, tgt) if fixed_phrase else ""
                issues.append(
                    DetectedIssue(
                        key=key,
                        lang=lang,
                        issue_type="machine_translation_suspect",
                        severity="medium",
                        source=src,
                        target=tgt,
                        evidence=reason,
                        suggestion=mt_sug,
                        confidence=0.89,
                        auto_fix_safe=False,
                    )
                )
                break

        # 8. inconsistent_term
        if key in inconsistent_keys:
            canonical, variants = inconsistent_keys[key]
            sample_vars = " / ".join(f"«{v}»" for v in variants[:3])
            issues.append(
                DetectedIssue(
                    key=key,
                    lang=lang,
                    issue_type="inconsistent_term",
                    severity="medium",
                    source=src,
                    target=tgt,
                    evidence=(
                        f"Бірдей түпнұсқа мәтін («{src}») файл ішінде әртүрлі аударылған: {sample_vars}."
                    ),
                    suggestion=canonical,
                    confidence=0.91,
                    auto_fix_safe=True,
                )
            )

        # 9 & 10. Kazakh suffix_harmony and orthography
        if lang == "kk":
            for sh_finding in check_kazakh_suffix_harmony(tgt):
                issues.append(
                    DetectedIssue(
                        key=key,
                        lang=lang,
                        issue_type=sh_finding.issue_type,
                        severity=sh_finding.severity,
                        source=src,
                        target=tgt,
                        evidence=sh_finding.evidence,
                        suggestion=sh_finding.suggestion,
                        confidence=sh_finding.confidence,
                        auto_fix_safe=sh_finding.auto_fix_safe,
                    )
                )

            for ortho_finding in check_kazakh_orthography(tgt, whitelist):
                issues.append(
                    DetectedIssue(
                        key=key,
                        lang=lang,
                        issue_type=ortho_finding.issue_type,
                        severity=ortho_finding.severity,
                        source=src,
                        target=tgt,
                        evidence=ortho_finding.evidence,
                        suggestion=ortho_finding.suggestion,
                        confidence=ortho_finding.confidence,
                        auto_fix_safe=ortho_finding.auto_fix_safe,
                    )
                )

        # 12. other_localization_issue (HTML/RichText tag mismatch, line-break mismatch, leaked null/NaN)
        src_tags = extract_html_tags(src)
        tgt_tags = extract_html_tags(tgt)
        if src_tags != tgt_tags:
            issues.append(
                DetectedIssue(
                    key=key,
                    lang=lang,
                    issue_type="other_localization_issue",
                    severity="high",
                    source=src,
                    target=tgt,
                    evidence=(
                        f"Пішімдеу/HTML тегтері сәйкес келмейді: түпнұсқада {src_tags or 'жоқ'}, "
                        f"аудармада {tgt_tags or 'жоқ'}."
                    ),
                    suggestion="",
                    confidence=0.96,
                    auto_fix_safe=False,
                )
            )
        elif src.count("\n") != tgt.count("\n"):
            issues.append(
                DetectedIssue(
                    key=key,
                    lang=lang,
                    issue_type="other_localization_issue",
                    severity="low",
                    source=src,
                    target=tgt,
                    evidence=(
                        f"Жол тасымалы (\\n) саны сәйкес емес: түпнұсқада {src.count(chr(10))}, "
                        f"аудармада {tgt.count(chr(10))}."
                    ),
                    suggestion="",
                    confidence=0.87,
                    auto_fix_safe=False,
                )
            )
        elif re.search(r"\b(undefined|NaN|\[object Object\])\b", tgt):
            issues.append(
                DetectedIssue(
                    key=key,
                    lang=lang,
                    issue_type="other_localization_issue",
                    severity="high",
                    source=src,
                    target=tgt,
                    evidence="Аударма ішінде техникалық қате мәні (undefined / NaN) қалып қойған.",
                    suggestion="",
                    confidence=0.99,
                    auto_fix_safe=False,
                )
            )

    return issues


def compute_quality_score(total_keys: int, issues: list[DetectedIssue]) -> float:
    """Compute a 0..100 localization quality score weighted by issue severity."""
    if total_keys <= 0:
        return 100.0
    penalty = 0.0
    for iss in issues:
        if iss.severity == "high":
            penalty += 1.0
        elif iss.severity == "medium":
            penalty += 0.55
        else:
            penalty += 0.25
    raw_score = max(0.0, 100.0 * (1.0 - (penalty / max(total_keys * 1.15, 1.0))))
    return round(raw_score, 1)
