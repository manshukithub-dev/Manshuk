from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time

# Use an isolated temporary SQLite database for automated tests so production DB starts clean
_TEST_DB_DIR = tempfile.mkdtemp(prefix="qazaq_locqa_test_")
os.environ["QAZAQ_LOCQA_DB_URL"] = f"sqlite:///{Path(_TEST_DB_DIR).as_posix()}/test.db"

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app, init_db_and_seeds
from backend.app.services.arb_parser import (
    ARBValidationError,
    export_fixed_arb,
    extract_icu_structure,
    parse_arb_content,
    validate_arb_for_gen_l10n,
)
from backend.app.services.glossary_service import INITIAL_GLOSSARY_TERMS
from backend.app.services.kazakh_nlp import (
    check_kazakh_orthography,
    check_kazakh_suffix_harmony,
    transliterate_kk_to_latin,
)
from backend.app.services.qa_engine import run_qa_checks
from backend.app.services.uzbek_nlp import check_uzbek_localization, is_likely_uzbek_text
from cli.locqa import main as cli_main


@pytest.fixture(scope="module")
def client():
    init_db_and_seeds()
    with TestClient(app) as c:
        yield c


# 1. ARB файлын оқу
def test_read_arb_file():
    raw = json.dumps(
        {
            "@@locale": "kk",
            "welcome_msg": "Қош келдіңіз, {name}!",
            "@welcome_msg": {
                "description": "Greeting on login screen",
                "placeholders": {"name": {"type": "String"}},
            },
        },
        ensure_ascii=False,
    )
    parsed = parse_arb_content(raw, "intl_kk.arb")
    assert parsed.locale == "kk"
    assert parsed.entries["welcome_msg"] == "Қош келдіңіз, {name}!"
    assert "welcome_msg" in parsed.metadata
    assert parsed.metadata["welcome_msg"]["description"] == "Greeting on login screen"


# 2 & 12 & 13. ARB файлын сақтау, Metadata сақтау және Экспортталған файлдың дұрыстығы
def test_save_export_arb_preserves_metadata_untouched_and_human_review():
    src_raw = json.dumps(
        {
            "@@locale": "ru",
            "unchanged_key": "Гараж",
            "@unchanged_key": {"description": "Garage header"},
            "garage_rent_button": "Арендовать",
            "@garage_rent_button": {"description": "Rent CTA"},
            "online_count": "{count, plural, one{{count} игрок} other{{count} игроков}}",
            "@online_count": {"placeholders": {"count": {"type": "int"}}},
        },
        ensure_ascii=False,
    )
    tgt_raw = json.dumps(
        {
            "@@locale": "kk",
            "unchanged_key": "Гараж",
            "@unchanged_key": {"description": "Garage header"},
            "garage_rent_button": "Жалға алу үшін басыңыз",
            "@garage_rent_button": {"description": "Rent CTA"},
            "online_count": "{count, plural, one{{count} ойыншы} other{{count} ойыншы}}",
            "@online_count": {"placeholders": {"count": {"type": "int"}}},
        },
        ensure_ascii=False,
    )
    updates = {
        "unchanged_key": {
            "current_target": "Гараж",
            "is_fixed": False,
            "reviewed_by_human": False,
        },
        "garage_rent_button": {
            "current_target": "Жалға алу",
            "is_fixed": True,
            "reviewed_by_human": True,
            "reviewer_name": "Айгерім Сейітова",
            "reviewed_at": "2026-10-30T12:00:00Z",
        },
        "online_count": {
            "current_target": "{count, plural, one{{count} ойыншы} other{{count} ойыншы}}",
            "is_fixed": False,
            "reviewed_by_human": True,
            "reviewer_name": "Айгерім Сейітова",
        },
    }
    exported_str, summary, warnings = export_fixed_arb(tgt_raw, src_raw, updates, target_locale="kk")
    assert not warnings
    assert summary["total_keys"] == 3
    assert summary["modified_keys"] == 1
    assert summary["human_verified_keys"] == 2

    exported_obj = json.loads(exported_str)
    assert exported_obj["@@locale"] == "kk"
    assert exported_obj["unchanged_key"] == "Гараж"
    assert exported_obj["@unchanged_key"] == {"description": "Garage header"}
    assert exported_obj["garage_rent_button"] == "Жалға алу"
    assert exported_obj["@garage_rent_button"]["description"] == "Rent CTA"
    assert exported_obj["@garage_rent_button"]["x-reviewed-by-human"] is True
    assert exported_obj["@garage_rent_button"]["x-reviewed-by"] == "Айгерім Сейітова"
    assert exported_obj["online_count"] == "{count, plural, one{{count} ойыншы} other{{count} ойыншы}}"
    errs, warns = validate_arb_for_gen_l10n(exported_obj, parse_arb_content(src_raw).entries)
    assert errs == []
    assert warns == []


# 3. Қате JSON және жарамсыз ARB құрылымы
def test_invalid_json_and_orphan_metadata():
    with pytest.raises(ARBValidationError) as exc_info:
        parse_arb_content('{"@@locale": "kk", "broken": "мәтін", }', "bad.arb")
    assert "JSON құрылымы қате" in str(exc_info.value)

    orphan_arb = json.dumps({"@@locale": "kk", "@ghost_key": {"description": "No value key"}})
    with pytest.raises(ARBValidationError) as orphan_exc:
        parse_arb_content(orphan_arb, "orphan.arb")
    assert "жетім метадеректер" in str(orphan_exc.value)


# 4. Жетіспейтін аударма және same_as_source
def test_missing_translation_and_same_as_source():
    src = {
        "missing_key": "Подключение к серверу...",
        "copied_key": "Недостаточно средств",
        "brand_key": "Grand Coins",
    }
    tgt = {
        "missing_key": "",
        "copied_key": "Недостаточно средств",
        "brand_key": "Grand Coins",
    }
    issues = run_qa_checks(src, tgt, lang="kk", glossary=INITIAL_GLOSSARY_TERMS)
    by_key = {i.key: i.issue_type for i in issues}
    assert by_key["missing_key"] == "untranslated"
    assert by_key["copied_key"] == "same_as_source"
    # Brand name Grand Coins must NOT be falsely flagged!
    assert "brand_key" not in by_key


# 5. Плейсхолдер сәйкессіздігі
def test_placeholder_mismatch():
    src = {"invite": "Игрок {sender} пригласил {receiver} в семью"}
    tgt = {"invite": "Ойыншы {sender} сізді отбасыға шақырды"}
    issues = run_qa_checks(src, tgt, lang="kk", glossary=INITIAL_GLOSSARY_TERMS)
    ph_issues = [i for i in issues if i.issue_type == "placeholder_mismatch"]
    assert len(ph_issues) == 1
    assert "{receiver}" in ph_issues[0].evidence


# 6. ICU plural тексеруі
def test_icu_plural_validation():
    src = {
        "players": "{count, plural, one{{count} игрок} other{{count} игроков}}",
        "valid_plural": "{count, plural, one{{count} машина} other{{count} машин}}",
    }
    tgt = {
        # Missing mandatory `other{...}` branch!
        "players": "{count, plural, one{{count} ойыншы}}",
        "valid_plural": "{count, plural, one{{count} көлік} other{{count} көлік}}",
    }
    issues = run_qa_checks(src, tgt, lang="kk", glossary=INITIAL_GLOSSARY_TERMS)
    plural_errs = [i for i in issues if i.issue_type == "plural_mismatch"]
    assert len(plural_errs) == 1
    assert plural_errs[0].key == "players"
    assert "other" in plural_errs[0].evidence

    ph, blocks, errs = extract_icu_structure(tgt["valid_plural"])
    assert "count" in ph
    assert len(blocks) == 1
    assert not errs


# 7. Глоссарий және ойын сленгін қорғау
def test_glossary_violation_and_slang_protection():
    src = {
        "family_msg": "Склад семьи пополнен",
        "donate_msg": "Купите 100 Grand Coins",
        "slang_ok": "Вам выдан 1 варн и мут на 10 мин, арендуйте фуру за 500 ГК во фракции",
    }
    tgt = {
        "family_msg": "Жанұя қоймасы толтырылды",  # Should be 'отбасы', not 'жанұя'
        "donate_msg": "100 Үлкен монеталар сатып алыңыз",  # Should keep 'Grand Coins'
        "slang_ok": "Сізге 1 варн және 10 мин мут берілді, фракцияда 500 ГК-ға фура жалға алыңыз",
    }
    issues = run_qa_checks(src, tgt, lang="kk", glossary=INITIAL_GLOSSARY_TERMS)
    fam_issues = [i for i in issues if i.key == "family_msg" and i.issue_type == "glossary_violation"]
    don_issues = [i for i in issues if i.key == "donate_msg" and i.issue_type == "glossary_violation"]
    slang_issues = [i for i in issues if i.key == "slang_ok"]

    assert len(fam_issues) == 1
    assert "отбасы" in fam_issues[0].suggestion.lower()
    assert len(don_issues) == 1
    assert "Grand Coins" in don_issues[0].suggestion
    assert slang_issues == []


# 8. Ұзын мәтін және қазақ латын транслитерациясы
def test_length_overflow_and_latin_transliteration():
    src = {"garage_rent_button": "Арендовать"}
    tgt = {"garage_rent_button": "Жалға алу үшін басыңыз"}
    issues = run_qa_checks(src, tgt, lang="kk", glossary=INITIAL_GLOSSARY_TERMS)
    overflow = [i for i in issues if i.issue_type == "length_overflow"]
    assert len(overflow) == 1
    assert overflow[0].severity == "high"
    assert overflow[0].suggestion == "Жалға алу"

    latin = transliterate_kk_to_latin("Қазақша әріптер: ә, ғ, қ, ң, ө, ұ, ү, і — {name}!")
    assert "Qazaqşa" in latin
    assert "{name}" in latin
    assert "ä" in latin and "ğ" in latin and "ñ" in latin and "ū" in latin and "ü" in latin


# 9. Қазақ әріптері (orthography)
def test_kazakh_orthography_and_homoglyphs():
    findings_ru_letters = check_kazakh_orthography("Ойыншылар тизими жане купия сөз")
    assert len(findings_ru_letters) == 1
    assert findings_ru_letters[0].issue_type == "orthography"
    assert "тізімі" in findings_ru_letters[0].suggestion
    assert "және" in findings_ru_letters[0].suggestion
    assert "құпия" in findings_ru_letters[0].suggestion

    # Latin 'i' mixed inside Cyrillic word 'тізімі'
    findings_homoglyph = check_kazakh_orthography("Көліктер тiзiмi")
    assert len(findings_homoglyph) == 1
    assert findings_homoglyph[0].suggestion == "Көліктер тізімі"


# 10. Қосымша үндестігі (suffix_harmony) — {name}-ға және сандық жалғаулар
def test_kazakh_suffix_harmony():
    dynamic_findings = check_kazakh_suffix_harmony("{name}-ға сыйлық жіберілді")
    assert len(dynamic_findings) == 1
    f = dynamic_findings[0]
    assert f.issue_type == "suffix_harmony"
    assert f.severity == "high"
    assert f.auto_fix_safe is False  # Must NEVER apply dangerous auto-fix!
    assert "{name}" in f.suggestion
    assert "-ға" not in f.suggestion
    assert "код деңгейінде" in f.evidence.lower()

    num_findings = check_kazakh_suffix_harmony("Сыйлық 5-ға деңгейден бастап беріледі")
    assert any(nf.suggestion == "Сыйлық 5-ке деңгейден бастап беріледі" for nf in num_findings)


# 11. Өзбек тілін анықтау және тексеру
def test_uzbek_language_detection_and_qa():
    assert is_likely_uzbek_text("Sovg'a o'yinchiga yuborildi") is True
    uz_findings = check_uzbek_localization(
        "Предложение обмена от {player}",
        "{player} томонидан алмашув таклифи",
    )
    assert any(f.issue_type == "wrong_language" for f in uz_findings)

    kk_in_uz = check_uzbek_localization("Список игроков", "Ойыншылар тізімі")
    assert any(f.issue_type == "wrong_language" for f in kk_in_uz)


# 14. 5 500-ден астам кілті бар файлдармен жылдамдық пен тұрақтылық тесті
def test_large_scale_5600_keys_performance():
    src = {}
    tgt = {}
    for idx in range(5600):
        k = f"game_str_{idx}"
        src[k] = f"Сообщение системы #{idx} для игрока {{name}}"
        if idx % 500 == 0:
            tgt[k] = f"{{name}}-ға жүйелік хабарлама #{idx}"
        else:
            tgt[k] = f"{{name}} атты ойыншыға жүйелік хабарлама #{idx}"

    t0 = time.perf_counter()
    issues = run_qa_checks(src, tgt, lang="kk", glossary=INITIAL_GLOSSARY_TERMS)
    elapsed = time.perf_counter() - t0

    assert len(src) == 5600
    assert len(issues) == 12  # indices 0, 500, 1000, ..., 5500
    assert elapsed < 5.0  # Fast O(N) processing


# 15. Full API workflow, security isolation, human review state, and CLI check
def test_api_end_to_end_and_cli(client: TestClient, tmp_path: Path):
    ws_a = {"X-Workspace-Id": "test-ws-alpha"}
    ws_b = {"X-Workspace-Id": "test-ws-beta"}

    # Invalid file extension rejected
    bad_ext = client.post(
        "/api/files/upload",
        data={"role": "kk"},
        files={"file": ("hack.exe", b"MZ...", "application/octet-stream")},
        headers=ws_a,
    )
    assert bad_ext.status_code == 400

    # Run DEMO QA check in workspace A
    demo_resp = client.post("/api/checks/demo", headers=ws_a)
    assert demo_resp.status_code == 200
    run_data = demo_resp.json()
    assert run_data["is_demo"] is True
    assert run_data["total_issues"] >= 10
    run_id = run_data["id"]

    # Workspace B must NOT see Workspace A's runs or files (security isolation!)
    runs_b = client.get("/api/checks", headers=ws_b).json()
    assert all(r["id"] != run_id for r in runs_b)

    # Batch auto-fix must keep reviewed_by_human == False!
    batch_resp = client.post(f"/api/issues/batch-auto-fix?run_id={run_id}", headers=ws_a)
    assert batch_resp.status_code == 200
    assert batch_resp.json()["reviewed_by_human"] is False

    dash_after_auto = client.get(f"/api/dashboard?run_id={run_id}", headers=ws_a).json()
    assert dash_after_auto["fixed_strings"] > 0
    assert dash_after_auto["human_reviewed_strings"] == 0

    # Human accepts/edits an issue -> reviewed_by_human becomes True!
    issues_list = client.get(f"/api/issues?run_id={run_id}", headers=ws_a).json()["items"]
    suffix_issue = next(i for i in issues_list if i["issue_type"] == "suffix_harmony")
    # Dangerous auto_apply on dynamic suffix_harmony must be blocked!
    blocked = client.post(
        f"/api/issues/{suffix_issue['id']}/action",
        json={"action": "auto_apply"},
        headers=ws_a,
    )
    assert blocked.status_code == 400

    # Human confirmation succeeds and sets reviewed_by_human = True
    human_ok = client.post(
        f"/api/issues/{suffix_issue['id']}/action",
        json={"action": "accept_suggestion", "reviewer_name": "Айгерім Сейітова"},
        headers=ws_a,
    )
    assert human_ok.status_code == 200
    assert human_ok.json()["reviewed_by_human"] is True

    # Export fixed ARB & JSON/HTML reports
    arb_resp = client.get(f"/api/reports/{run_id}/export-arb?lang=kk", headers=ws_a)
    assert arb_resp.status_code == 200
    exported_arb = json.loads(arb_resp.text)
    assert exported_arb["@gift_sent_notification"]["x-reviewed-by-human"] is True

    json_rep = client.get(f"/api/reports/{run_id}/json", headers=ws_a)
    assert json_rep.status_code == 200
    rep_items = json.loads(json_rep.text)
    assert isinstance(rep_items, list) and len(rep_items) > 0
    assert set(rep_items[0].keys()) == {
        "key",
        "issue_type",
        "severity",
        "source",
        "target",
        "evidence",
        "suggestion",
        "confidence",
        "reviewed_by_human",
    }

    html_rep = client.get(f"/api/reports/{run_id}/html", headers=ws_a)
    assert html_rep.status_code == 200
    assert "QAZAQ LOC QA" in html_rep.text

    # Settings masks API key and never returns raw key
    put_set = client.put(
        "/api/settings",
        json={
            "llm_provider": "gemini",
            "llm_api_key": "AIzaSySecretTestKey123456789",
            "llm_model": "gemini-2.5-flash",
            "llm_base_url": "",
            "length_overflow_ratio": 1.45,
            "button_max_chars": 24,
            "latin_check_enabled": True,
        },
    )
    assert put_set.status_code == 200
    set_body = put_set.json()
    assert set_body["has_api_key"] is True
    assert "SecretTestKey" not in set_body["masked_api_key"]
    # Clear test key afterwards so clean rule-engine default remains
    client.put(
        "/api/settings",
        json={
            "llm_provider": "gemini",
            "clear_api_key": True,
            "llm_model": "gemini-2.5-flash",
            "llm_base_url": "",
            "length_overflow_ratio": 1.45,
            "button_max_chars": 24,
            "latin_check_enabled": True,
        },
    )

    # CLI test
    out_json = tmp_path / "cli_report.json"
    out_html = tmp_path / "cli_report.html"
    out_arb = tmp_path / "intl_kk_fixed.arb"
    rc = cli_main(
        [
            "check",
            "--source",
            "data/demo/intl_ru.arb",
            "--target",
            "data/demo/intl_kk.arb",
            "--glossary",
            "glossary/glossary.csv",
            "--out",
            str(out_json),
            "--html",
            str(out_html),
            "--fixed-arb",
            str(out_arb),
        ]
    )
    assert rc == 0
    assert out_json.exists()
    assert out_html.exists()
    assert out_arb.exists()


def test_production_postgres_url_and_cors_readiness():
    from sqlalchemy import create_engine
    from fastapi.testclient import TestClient
    from backend.app.config import normalize_database_url
    from backend.app.main import app

    # 1. Render / Neon / Heroku Postgres URL normalization
    assert (
        normalize_database_url("postgres://user:pass@dpg-xyz.render.com:5432/qazaq_db")
        == "postgresql+psycopg://user:pass@dpg-xyz.render.com:5432/qazaq_db"
    )
    assert (
        normalize_database_url("postgresql://user:pass@ep-cool.neon.tech/neondb?sslmode=require")
        == "postgresql+psycopg://user:pass@ep-cool.neon.tech/neondb?sslmode=require"
    )
    assert (
        normalize_database_url("postgresql+psycopg2://user:pass@localhost:5432/qazaq_db")
        == "postgresql+psycopg://user:pass@localhost:5432/qazaq_db"
    )
    assert normalize_database_url("sqlite:///./data/qazaq_locqa.db") == "sqlite:///./data/qazaq_locqa.db"

    # 2. Verify SQLAlchemy + psycopg v3 dialect instantiates cleanly without connecting
    pg_engine = create_engine(
        normalize_database_url("postgres://user:pass@localhost:5432/qazaq_locqa"),
        pool_pre_ping=True,
    )
    assert pg_engine.dialect.name == "postgresql"
    assert pg_engine.dialect.driver == "psycopg"
    pg_engine.dispose()

    # 3. Verify root status, /api/health DB probe, and Vercel CORS preflight
    with TestClient(app) as client:
        root_r = client.get("/")
        assert root_r.status_code == 200
        assert root_r.json()["status"] == "online"

        health_r = client.get("/api/health")
        assert health_r.status_code == 200
        assert health_r.json()["status"] == "ok"
        assert "database" in health_r.json()

        cors_r = client.options(
            "/api/dashboard",
            headers={
                "Origin": "https://qazaq-loc-qa.vercel.app",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-Workspace-Id,Content-Type",
            },
        )
        assert cors_r.status_code == 200
        assert cors_r.headers.get("access-control-allow-origin") == "https://qazaq-loc-qa.vercel.app"

