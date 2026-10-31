from __future__ import annotations

import re
from dataclasses import dataclass

KAZAKH_SPECIFIC_CHARS = set("әғқңөұүһіӘҒҚҢӨҰҮҺІ")
RUSSIAN_ONLY_CYRILLIC = set("щъэёЩЪЭЁ")

BACK_VOWELS = set("аоұыАОҰЫяуЯУ")
FRONT_VOWELS = set("әеіөүӘЕІӨҮэиЭИ")
VOICELESS_CONSONANTS = set("кқпстфхцчшщКҚПСТФХЦЧШЩ")

# Placeholder + attached Kazakh suffix (with or without hyphen/apostrophe)
PLACEHOLDER_SUFFIX_RE = re.compile(
    r"(\{[a-zA-Z_][a-zA-Z0-9_]*\}|%[sd]|\$\d+)"
    r"([-–']?)"
    r"(ға|ге|қа|ке|на|не|дан|ден|тан|тен|нан|нен|ның|нің|дың|дің|тың|тің|"
    r"ды|ді|ты|ті|ны|ні|да|де|та|те|нда|нде|мен|бен|пен|лар|лер|дар|дер|тар|тер"
    r"(?:ға|ге|қа|ке|дан|ден|ның|нің|ды|ді|мен|да|де)?)\b",
    re.IGNORECASE,
)

# Number + dative/locative/ablative suffix check in Kazakh
NUMBER_SUFFIX_RE = re.compile(
    r"\b(\d+)-(ға|ге|қа|ке|да|де|та|те|дан|ден|тан|тен)\b",
    re.IGNORECASE,
)

# Mixed Latin homoglyphs inside Cyrillic words (excluding placeholders/tags)
MIXED_SCRIPT_TOKEN_RE = re.compile(r"\b(?=[а-яА-ЯәғқңөұүһіӘҒҚҢӨҰҮҺІa-zA-Z]*[а-яА-ЯәғқңөұүһіӘҒҚҢӨҰҮҺІ])(?=[а-яА-ЯәғқңөұүһіӘҒҚҢӨҰҮҺІa-zA-Z]*[a-zA-Z])[а-яА-ЯәғқңөұүһіӘҒҚҢӨҰҮҺІa-zA-Z]+\b")

LATIN_TO_CYRILLIC_HOMOGLYPHS = {
    "i": "і",
    "I": "І",
    "a": "а",
    "A": "А",
    "e": "е",
    "E": "Е",
    "o": "о",
    "O": "О",
    "c": "с",
    "C": "С",
    "p": "р",
    "P": "Р",
    "x": "х",
    "X": "Х",
    "y": "у",
    "k": "к",
    "K": "К",
}

# Common Kazakh words frequently mistyped with Russian keyboard letters instead of ә,ғ,қ,ң,ө,ұ,ү,һ,і
KAZAKH_ORTHO_CORRECTIONS: dict[str, str] = {
    "казакша": "қазақша",
    "казак": "қазақ",
    "кате": "қате",
    "кателер": "қателер",
    "акша": "ақша",
    "гана": "ғана",
    "ушін": "үшін",
    "ушин": "үшін",
    "жане": "және",
    "тизим": "тізім",
    "тизими": "тізімі",
    "тізіми": "тізімі",
    "купия": "құпия",
    "койма": "қойма",
    "коймасы": "қоймасы",
    "мумкин": "мүмкін",
    "мүмкин": "мүмкін",
    "оширу": "өшіру",
    "киру": "кіру",
    "шыгу": "шығу",
    "косу": "қосу",
    "озгерту": "өзгерту",
    "жиберу": "жіберу",
    "жиберилди": "жіберілді",
    "жіберілди": "жіберілді",
    "колик": "көлік",
    "сатти": "сәтті",
    "денгей": "деңгей",
    "денгейі": "деңгейі",
    "кару": "қару",
    "корганыс": "қорғаныс",
    "ойыншыга": "ойыншыға",
    "басыныз": "басыңыз",
    "танданыз": "таңдаңыз",
    "растаныз": "растаңыз",
    "кутиниз": "күтіңіз",
    "енгизиниз": "енгізіңіз",
    "жеткиликсиз": "жеткіліксіз",
    "сыйлык": "сыйлық",
    "куттыктаймыз": "құттықтаймыз",
    "тиркелу": "тіркелу",
    "жалга": "жалға",
    "сатып алыныз": "сатып алыңыз",
    "озгерис": "өзгеріс",
    "кауипсиздик": "қауіпсіздік",
    "баптаулар": "баптаулар",
}

POLITE_IMPERATIVE_MIS_RE = re.compile(
    r"\b([а-яА-ЯәғқңөұүһіӘҒҚҢӨҰҮҺІ]{2,})(ыныз|иниз|ініз)\b"
)

# Official 2021 Qazaq Latin Alphabet mapping
CYR_TO_QAZAQ_LATIN: dict[str, str] = {
    "А": "A", "а": "a",
    "Ә": "Ä", "ә": "ä",
    "Б": "B", "б": "b",
    "В": "V", "в": "v",
    "Г": "G", "г": "g",
    "Ғ": "Ğ", "ғ": "ğ",
    "Д": "D", "д": "d",
    "Е": "E", "е": "e",
    "Ё": "Yo", "ё": "yo",
    "Ж": "J", "ж": "j",
    "З": "Z", "з": "z",
    "И": "İ", "и": "i",
    "Й": "İ", "й": "i",
    "К": "K", "к": "k",
    "Қ": "Q", "қ": "q",
    "Л": "L", "л": "l",
    "М": "M", "м": "m",
    "Н": "N", "н": "n",
    "Ң": "Ñ", "ң": "ñ",
    "О": "O", "о": "o",
    "Ө": "Ö", "ө": "ö",
    "П": "P", "п": "p",
    "Р": "R", "р": "r",
    "С": "S", "с": "s",
    "Т": "T", "т": "t",
    "У": "U", "у": "u",
    "Ұ": "Ū", "ұ": "ū",
    "Ү": "Ü", "ү": "ü",
    "Ф": "F", "ф": "f",
    "Х": "H", "х": "h",
    "Һ": "H", "һ": "h",
    "Ц": "Ts", "ц": "ts",
    "Ч": "Ç", "ч": "ç",
    "Ш": "Ş", "ш": "ş",
    "Щ": "Ş", "щ": "ş",
    "Ъ": "", "ъ": "",
    "Ы": "Y", "ы": "y",
    "І": "I", "і": "ı",
    "Ь": "", "ь": "",
    "Э": "E", "э": "e",
    "Ю": "Yu", "ю": "yu",
    "Я": "Ya", "я": "ya",
}

PROTECTED_SEGMENT_RE = re.compile(r"(\{[^{}]*\}|</?[a-zA-Z][^>]*>|%[sdif]|\$\d+)")


@dataclass
class LinguisticFinding:
    issue_type: str
    severity: str
    evidence: str
    suggestion: str
    confidence: float
    auto_fix_safe: bool = True


def strip_placeholders_and_tags(text: str) -> str:
    return PROTECTED_SEGMENT_RE.sub(" ", text)


def transliterate_kk_to_latin(text: str) -> str:
    """
    Transliterate Kazakh Cyrillic text to the official Qazaq Latin alphabet,
    preserving {placeholders}, %s tokens, and <HTML> tags intact.
    """
    parts = PROTECTED_SEGMENT_RE.split(text)
    result: list[str] = []
    for idx, part in enumerate(parts):
        if idx % 2 == 1:
            # Protected placeholder or tag
            result.append(part)
        else:
            converted = "".join(CYR_TO_QAZAQ_LATIN.get(ch, ch) for ch in part)
            result.append(converted)
    return "".join(result)


def _expected_number_phonology(num_str: str) -> tuple[bool, bool]:
    """
    Return (is_front_vowel, is_voiceless_ending) for a Kazakh numeral reading!
    E.g.:
      1 (бір) -> front, voiced
      2 (екі) -> front, vowel
      3 (үш) -> front, voiceless (ш)
      4 (төрт) -> front, voiceless (т)
      5 (бес) -> front, voiceless (с)
      6 (алты) -> back, vowel
      7 (жеті) -> front, vowel
      8 (сегіз) -> front, voiced
      9 (тоғыз) -> back, voiced
      10 (он) -> back, voiced
      20 (жиырма) -> back, vowel
      30 (отыз) -> back, voiced
      40 (қырық) -> back, voiceless (қ)
      50 (елу) -> back/u, voiced -> 50-ге (елуге)
      60 (алпыс) -> back, voiceless (с) -> 60-қа
      70 (жетпіс) -> front, voiceless (с) -> 70-ке
      80 (сексен) -> front, voiced -> 80-ге
      90 (тоқсан) -> back, voiced -> 90-ға
      100 (жүз) -> front, voiced -> 100-ге
      1000 (мың) -> back, voiced -> 1000-ға
    """
    n = int(num_str)
    if n == 0:
        return True, False  # нөл -> нөлге
    last_digit = n % 10
    if last_digit != 0:
        mapping = {
            1: (True, False),
            2: (True, False),
            3: (True, True),
            4: (True, True),
            5: (True, True),
            6: (False, False),
            7: (True, False),
            8: (True, False),
            9: (False, False),
        }
        return mapping[last_digit]
    last_two = n % 100
    if last_two != 0:
        tens_map = {
            10: (False, False),
            20: (False, False),
            30: (False, False),
            40: (False, True),
            50: (True, False),
            60: (False, True),
            70: (True, True),
            80: (True, False),
            90: (False, False),
        }
        return tens_map.get(last_two, (False, False))
    if n % 1000 != 0:
        return True, False  # жүз -> жүзге
    return False, False  # мың -> мыңға


def _harmonious_number_suffix(num_str: str, raw_suffix: str) -> str:
    is_front, is_voiceless = _expected_number_phonology(num_str)
    s = raw_suffix.lower()
    if s in ("ға", "ге", "қа", "ке"):
        if is_voiceless:
            return "ке" if is_front else "қа"
        return "ге" if is_front else "ға"
    if s in ("да", "де", "та", "те"):
        if is_voiceless:
            return "те" if is_front else "та"
        return "де" if is_front else "да"
    if s in ("дан", "ден", "тан", "тен"):
        if is_voiceless:
            return "тен" if is_front else "тан"
        return "ден" if is_front else "дан"
    return raw_suffix


def restructure_placeholder_suffix_sentence(text: str, ph: str, suffix: str) -> str:
    """
    Suggest a natural Kazakh sentence restructuring that avoids attaching a hardcoded
    case/plural suffix directly to a runtime placeholder like `{name}-ға`.
    """
    s_lower = suffix.lower()
    # Special clean restructurings for common game notifications
    dative_pattern = re.compile(
        rf"^\s*{re.escape(ph)}[-–']?(?:ға|ге|қа|ке)\s+(.+?)\s*([.!?;]*)\s*$",
        re.IGNORECASE,
    )
    m_dat = dative_pattern.match(text)
    if m_dat:
        body, punct = m_dat.group(1), m_dat.group(2)
        if "сыйлық" in body.lower():
            return f"Сыйлық алушы — {ph} ({body}){punct}" if "жіберілді" not in body.lower() else f"Сыйлық {ph} атты ойыншыға жіберілді{punct}"
        return f"{body[:1].upper() + body[1:]} (ойыншы: {ph}){punct}"

    ablative_pattern = re.compile(
        rf"^\s*{re.escape(ph)}[-–']?(?:дан|ден|тан|тен|нан|нен)\s+(.+?)\s*([.!?;]*)\s*$",
        re.IGNORECASE,
    )
    m_abl = ablative_pattern.match(text)
    if m_abl:
        body, punct = m_abl.group(1), m_abl.group(2)
        return f"{body[:1].upper() + body[1:]} (жіберуші: {ph}){punct}"

    # Generic safe replacement using appositive helper noun if placeholder looks like player/name/user
    ph_lower = ph.lower()
    is_person = any(tok in ph_lower for tok in ("name", "player", "user", "nick", "admin", "sender", "target", "member"))
    if is_person:
        helper_map = {
            "ға": "атты ойыншыға", "ге": "атты ойыншыға", "қа": "атты ойыншыға", "ке": "атты ойыншыға",
            "дан": "атты ойыншыдан", "ден": "атты ойыншыдан", "тан": "атты ойыншыдан", "тен": "атты ойыншыдан",
            "ның": "ойыншысының", "нің": "ойыншысының", "дың": "ойыншысының", "дің": "ойыншысының",
            "ды": "ойыншысын", "ді": "ойыншысын", "ты": "ойыншысын", "ті": "ойыншысын",
            "мен": "ойыншысымен", "бен": "ойыншысымен", "пен": "ойыншысымен",
            "да": "ойыншысында", "де": "ойыншысында",
        }
        replacement_noun = helper_map.get(s_lower)
        if replacement_noun:
            return re.sub(
                rf"{re.escape(ph)}[-–']?{re.escape(suffix)}\b",
                f"{ph} {replacement_noun}",
                text,
                count=1,
            )

    # Fallback: remove static suffix and rewrite as colon/parenthetical structure
    cleaned = re.sub(rf"{re.escape(ph)}[-–']?{re.escape(suffix)}\b", ph, text, count=1)
    return f"{cleaned} [Код деңгейінде жалғауды динамикалық таңдаңыз немесе сөйлемді қайта құрастырыңыз]"


def check_kazakh_suffix_harmony(target: str) -> list[LinguisticFinding]:
    """
    Check Kazakh suffix harmony (Section 8):
    1. Runtime placeholder + static suffix (`{name}-ға`, `{name}-ден`, etc.) -> High priority, no auto-fix, human review required.
    2. Number + disharmonious suffix (`5-ға` -> `5-ке`, `10-ге` -> `10-ға`).
    3. Pure Kazakh stem + disharmonious case/plural suffix.
    """
    findings: list[LinguisticFinding] = []

    # 1. Dynamic placeholder with hardcoded Kazakh suffix
    for match in PLACEHOLDER_SUFFIX_RE.finditer(target):
        ph, sep, suffix = match.group(1), match.group(2), match.group(3)
        full_token = f"{ph}{sep}{suffix}"
        restructured = restructure_placeholder_suffix_sentence(target, ph, suffix)
        findings.append(
            LinguisticFinding(
                issue_type="suffix_harmony",
                severity="high",
                evidence=(
                    f"«{full_token}» тіркесіндегі {ph} мәні тек ойын жұмыс істеп тұрғанда (runtime) белгілі болады. "
                    f"Тұрақты «{sep}{suffix}» жалғауы ойыншы атының соңғы дыбысы мен жуан-жіңішкелігіне сәйкес келмей қалады "
                    f"(мысалы: «Әлішер-ға» немесе «Серік-ға» — қате). "
                    f"Шешім: (1) сөйлемді жалғаусыз/көмекші сөз арқылы қайта құрастырыңыз немесе "
                    f"(2) қосымшаны код деңгейінде (KazakhSuffixHelper) динамикалық түрде жалғаңыз. "
                    f"Қауіпті автоматты түзету қолданылмайды — маманның тексеруі қажет."
                ),
                suggestion=restructured,
                confidence=0.97,
                auto_fix_safe=False,
            )
        )

    # 2. Numeric suffix harmony (e.g., 5-ға -> 5-ке)
    for match in NUMBER_SUFFIX_RE.finditer(target):
        num_str, suffix = match.group(1), match.group(2)
        expected = _harmonious_number_suffix(num_str, suffix)
        if expected.lower() != suffix.lower():
            fixed_text = target[: match.start()] + f"{num_str}-{expected}" + target[match.end() :]
            findings.append(
                LinguisticFinding(
                    issue_type="suffix_harmony",
                    severity="medium",
                    evidence=(
                        f"Сандық жалғау үндестік заңына сәйкес келмейді: «{num_str}-{suffix}» емес, "
                        f"қазақ тілінің дыбыс үндестігі бойынша «{num_str}-{expected}» болуы тиіс."
                    ),
                    suggestion=fixed_text,
                    confidence=0.95,
                    auto_fix_safe=True,
                )
            )
            break

    # 3. Stem + suffix vowel harmony check on words containing Kazakh letters
    cleaned = strip_placeholders_and_tags(target)
    words = re.findall(r"[а-яА-ЯәғқңөұүһіӘҒҚҢӨҰҮҺІ]{4,}", cleaned)
    suffix_pairs = [
        ("лар", "лер"), ("дар", "дер"), ("тар", "тер"),
        ("ға", "ге"), ("қа", "ке"),
        ("дан", "ден"), ("тан", "тен"),
    ]
    for word in words:
        w_low = word.lower()
        for back_suf, front_suf in suffix_pairs:
            if w_low.endswith(front_suf) and len(w_low) > len(front_suf) + 2:
                stem = w_low[: -len(front_suf)]
                has_back = any(ch in BACK_VOWELS for ch in stem)
                has_front = any(ch in FRONT_VOWELS for ch in stem)
                # Pure back stem with Kazakh back letter қ/ғ/ұ + front suffix is definitely broken harmony
                if has_back and not has_front and any(ch in "қғұыао" for ch in stem):
                    corrected_word = word[: -len(front_suf)] + back_suf
                    findings.append(
                        LinguisticFinding(
                            issue_type="suffix_harmony",
                            severity="medium",
                            evidence=(
                                f"«{word}» сөзіндегі жуан түбірге жіңішке «-{front_suf}» қосымшасы жалғанған "
                                f"(үндестік заңы бұзылған)."
                            ),
                            suggestion=target.replace(word, corrected_word, 1),
                            confidence=0.9,
                            auto_fix_safe=True,
                        )
                    )
                    break
            elif w_low.endswith(back_suf) and len(w_low) > len(back_suf) + 2:
                stem = w_low[: -len(back_suf)]
                has_back = any(ch in BACK_VOWELS for ch in stem)
                has_front = any(ch in FRONT_VOWELS for ch in stem)
                if has_front and not has_back and any(ch in "әіөүң" for ch in stem):
                    corrected_word = word[: -len(back_suf)] + front_suf
                    findings.append(
                        LinguisticFinding(
                            issue_type="suffix_harmony",
                            severity="medium",
                            evidence=(
                                f"«{word}» сөзіндегі жіңішке түбірге жуан «-{back_suf}» қосымшасы жалғанған "
                                f"(үндестік заңы бұзылған)."
                            ),
                            suggestion=target.replace(word, corrected_word, 1),
                            confidence=0.9,
                            auto_fix_safe=True,
                        )
                    )
                    break

    return findings


def check_kazakh_orthography(target: str, whitelisted_tokens: set[str] | None = None) -> list[LinguisticFinding]:
    """
    Check Kazakh orthography (Section 8):
    - Specific Kazakh letters (ә, ғ, қ, ң, ө, ұ, ү, һ, і) replaced by Russian lookalikes.
    - Mixed Latin/Cyrillic homoglyphs inside Kazakh words (e.g. Latin 'i' instead of Kazakh 'і').
    - Polite imperative '-ыныз/-иниз' instead of '-ыңыз/-іңіз'.
    """
    findings: list[LinguisticFinding] = []
    whitelist = {w.lower() for w in (whitelisted_tokens or set())}
    stripped = strip_placeholders_and_tags(target)

    # 1. Mixed Latin + Cyrillic homoglyphs inside a single word
    for m in MIXED_SCRIPT_TOKEN_RE.finditer(stripped):
        bad_word = m.group(0)
        if bad_word.lower() in whitelist:
            continue
        fixed_word = "".join(LATIN_TO_CYRILLIC_HOMOGLYPHS.get(ch, ch) for ch in bad_word)
        if fixed_word != bad_word:
            findings.append(
                LinguisticFinding(
                    issue_type="orthography",
                    severity="high",
                    evidence=(
                        f"«{bad_word}» сөзінде кирилл әріптерінің ішіне латын таңбасы араласып кеткен "
                        f"(мысалы, қазақтың «і» әрпінің орнына латынша «i» жазылған)."
                    ),
                    suggestion=target.replace(bad_word, fixed_word, 1),
                    confidence=0.98,
                    auto_fix_safe=True,
                )
            )
            return findings

    # 2. Known Kazakh words written with Russian letters instead of ә, ғ, қ, ң, ө, ұ, ү, һ, і
    suggestion = target
    replaced_pairs: list[tuple[str, str]] = []
    for wrong, right in KAZAKH_ORTHO_CORRECTIONS.items():
        pattern = re.compile(rf"\b{re.escape(wrong)}\b", re.IGNORECASE)
        match = pattern.search(stripped)
        if match:
            found_tok = match.group(0)
            if found_tok.lower() in whitelist:
                continue
            replacement = right.capitalize() if found_tok[0].isupper() else right
            suggestion = pattern.sub(replacement, suggestion, count=1)
            replaced_pairs.append((found_tok, replacement))

    # 3. Polite imperative suffix (-ыныз / -иниз -> -ыңыз / -іңіз)
    for m in POLITE_IMPERATIVE_MIS_RE.finditer(stripped):
        full_word = m.group(0)
        stem, bad_end = m.group(1), m.group(2)
        is_front = any(ch in FRONT_VOWELS for ch in stem)
        good_end = "іңіз" if is_front or bad_end in ("иниз", "ініз") else "ыңыз"
        good_word = stem + good_end
        if (full_word, good_word) not in replaced_pairs:
            suggestion = suggestion.replace(full_word, good_word, 1)
            replaced_pairs.append((full_word, good_word))

    if replaced_pairs:
        examples_str = ", ".join(f"«{w}» → «{r}»" for w, r in replaced_pairs[:3])
        findings.append(
            LinguisticFinding(
                issue_type="orthography",
                severity="high",
                evidence=(
                    f"Қазақтың төл әріптерінің (ә, ғ, қ, ң, ө, ұ, ү, һ, і) орнына орыс әріптері қолданылған: {examples_str}."
                ),
                suggestion=suggestion,
                confidence=0.95,
                auto_fix_safe=True,
            )
        )

    return findings
