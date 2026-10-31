from __future__ import annotations

import csv
import io
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.config import GLOSSARY_DIR
from backend.app.models import GlossaryTerm

INITIAL_GLOSSARY_TERMS = [
    {
        "ru_term": "фракция",
        "kk_term": "фракция",
        "uz_term": "fraksiya",
        "en_term": "Fraction",
        "description": "Ойын ішіндегі мемлекеттік немесе рөлдік ұйым (полиция, армия, аурухана т.б.).",
        "example": "Сіз полиция фракциясына қабылдандыңыз.",
        "is_slang_or_brand": True,
    },
    {
        "ru_term": "семья",
        "kk_term": "отбасы",
        "uz_term": "oila",
        "en_term": "Family",
        "description": "Ойыншылар құратын бірлестік / клан жүйесі. Орысша «семья» әрдайым «отбасы» деп аударылады.",
        "example": "Отбасы қоймасына 50 000 ₸ салынды.",
        "is_slang_or_brand": False,
    },
    {
        "ru_term": "Grand Coins",
        "kk_term": "Grand Coins",
        "uz_term": "Grand Coins",
        "en_term": "Grand Coins",
        "description": "Ойынның ресми донат валютасы (бренд). Ешқашан сөзбе-сөз аударылмайды.",
        "example": "Шотыңызға 250 Grand Coins түсті.",
        "is_slang_or_brand": True,
    },
    {
        "ru_term": "бизнес",
        "kk_term": "бизнес",
        "uz_term": "biznes",
        "en_term": "Business",
        "description": "Ойыншы иелік ететін табыс көзі (дүкен, ЖМҚС, автосалон).",
        "example": "Сіздің бизнесіңіз салық төленбегендіктен жабылды.",
        "is_slang_or_brand": True,
    },
    {
        "ru_term": "варн",
        "kk_term": "варн",
        "uz_term": "varn",
        "en_term": "Warn",
        "description": "Әкімшілік ескерту жазасы (ойыншылар арасында қалыптасқан RP сленгі).",
        "example": "Ережені бұзғаныңыз үшін 1 варн берілді.",
        "is_slang_or_brand": True,
    },
    {
        "ru_term": "мут",
        "kk_term": "мут",
        "uz_term": "mut",
        "en_term": "Mute",
        "description": "Чатта жазуды уақытша бұғаттау жазасы (қалыптасқан ойын термині).",
        "example": "Сізге 30 минутқа мут берілді.",
        "is_slang_or_brand": True,
    },
    {
        "ru_term": "фура",
        "kk_term": "фура",
        "uz_term": "fura",
        "en_term": "Truck",
        "description": "Жүк тасымалдаушы ауыр көлік (алыс рейс жұмысында қолданылатын термин).",
        "example": "Фураны жалға алып, жүкті портқа жеткізіңіз.",
        "is_slang_or_brand": True,
    },
    {
        "ru_term": "ГК",
        "kk_term": "ГК",
        "uz_term": "GK",
        "en_term": "GC",
        "description": "Grand Coins валютасының ресми қысқартылған атауы.",
        "example": "VIP мәртебесінің бағасы: 500 ГК.",
        "is_slang_or_brand": True,
    },
]


def seed_default_glossary(db: Session) -> None:
    count = db.scalar(select(GlossaryTerm.id).limit(1))
    if count is not None:
        return

    default_csv = GLOSSARY_DIR / "glossary.csv"
    if default_csv.exists():
        raw = default_csv.read_text(encoding="utf-8")
        terms = parse_glossary_csv(raw)
        if terms:
            for item in terms:
                db.add(GlossaryTerm(**item))
            db.commit()
            return

    for item in INITIAL_GLOSSARY_TERMS:
        db.add(GlossaryTerm(**item))
    db.commit()


def parse_glossary_csv(csv_text: str) -> list[dict]:
    """
    Parse CSV glossary supporting both English headers (`ru_term,kk_term,uz_term,en_term,description,example`)
    and Kazakh/Russian headers (`Орысша термин,Қазақша термин,...`).
    """
    cleaned = csv_text.lstrip("\ufeff").strip()
    if not cleaned:
        return []

    reader = csv.DictReader(io.StringIO(cleaned))
    if not reader.fieldnames:
        return []

    def _pick(row: dict, candidates: list[str], default: str = "") -> str:
        for key in row:
            if key and key.strip().lower() in candidates:
                return (row[key] or "").strip()
        return default

    parsed: list[dict] = []
    for row in reader:
        ru = _pick(row, ["ru_term", "ru", "source", "орысша", "орысша термин", "русский"])
        kk = _pick(row, ["kk_term", "kk", "target", "қазақша", "қазақша термин", "казахский"])
        uz = _pick(row, ["uz_term", "uz", "өзбекше", "өзбекше термин", "узбекский"])
        en = _pick(row, ["en_term", "en", "english", "ағылшынша", "ағылшынша термин"])
        desc = _pick(row, ["description", "desc", "түсіндірме", "сипаттама", "описание"])
        ex = _pick(row, ["example", "usage", "қолданылу мысалы", "мысал", "пример"])
        slang_raw = _pick(row, ["is_slang_or_brand", "slang", "brand"], "false").lower()
        is_slang = slang_raw in ("true", "1", "yes", "иә") or (ru.lower() == kk.lower() and len(ru) >= 2)
        if ru and kk:
            parsed.append(
                {
                    "ru_term": ru,
                    "kk_term": kk,
                    "uz_term": uz,
                    "en_term": en,
                    "description": desc,
                    "example": ex,
                    "is_slang_or_brand": is_slang,
                }
            )
    return parsed


def export_glossary_csv(terms: list[GlossaryTerm]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["ru_term", "kk_term", "uz_term", "en_term", "description", "example", "is_slang_or_brand"]
    )
    for t in terms:
        writer.writerow(
            [
                t.ru_term,
                t.kk_term,
                t.uz_term or "",
                t.en_term or "",
                t.description or "",
                t.example or "",
                "true" if t.is_slang_or_brand else "false",
            ]
        )
    return buf.getvalue()


def load_glossary_dicts_from_file(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    return parse_glossary_csv(raw)
