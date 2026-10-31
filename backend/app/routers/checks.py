from __future__ import annotations

from pathlib import Path
import json
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from backend.app.config import DEMO_DIR
from backend.app.database import get_db
from backend.app.models import GlossaryTerm, ProjectRun, QAIssue, TranslationEntry, UploadedFile
from backend.app.routers.deps import get_workspace_token
from backend.app.schemas import (
    ProjectRunOut,
    RunCreateRequest,
    TransliterateOut,
    TransliterateRequest,
)
from backend.app.services.arb_parser import parse_arb_content
from backend.app.services.glossary_service import parse_glossary_csv
from backend.app.services.kazakh_nlp import transliterate_kk_to_latin
from backend.app.services.llm_service import enrich_issues_with_llm, get_setting
from backend.app.services.qa_engine import EngineConfig, compute_quality_score, run_qa_checks

router = APIRouter(prefix="/api", tags=["checks"])


def _execute_qa_pipeline(
    db: Session,
    workspace_token: str,
    run_name: str,
    is_demo: bool,
    ru_file: UploadedFile,
    kk_file: UploadedFile | None,
    uz_file: UploadedFile | None,
    en_file: UploadedFile | None,
    glossary_file: UploadedFile | None,
    use_llm: bool = True,
) -> ProjectRun:
    t0 = time.perf_counter()

    ru_parsed = parse_arb_content(ru_file.raw_content or "", ru_file.original_filename)
    kk_parsed = parse_arb_content(kk_file.raw_content or "", kk_file.original_filename) if kk_file else None
    uz_parsed = parse_arb_content(uz_file.raw_content or "", uz_file.original_filename) if uz_file else None
    en_parsed = parse_arb_content(en_file.raw_content or "", en_file.original_filename) if en_file else None

    if not kk_parsed and not uz_parsed:
        raise HTTPException(
            status_code=400,
            detail="Кемінде бір мақсатты аударма файлын (intl_kk.arb немесе intl_uz.arb) таңдаңыз.",
        )

    # Combine DB glossary with optional uploaded CSV glossary
    db_terms = db.scalars(select(GlossaryTerm)).all()
    glossary_map: dict[str, dict] = {
        t.ru_term.strip().lower(): {
            "ru_term": t.ru_term,
            "kk_term": t.kk_term,
            "uz_term": t.uz_term,
            "en_term": t.en_term,
            "description": t.description,
            "example": t.example,
            "is_slang_or_brand": t.is_slang_or_brand,
        }
        for t in db_terms
    }
    if glossary_file and glossary_file.raw_content:
        for row in parse_glossary_csv(glossary_file.raw_content):
            glossary_map[row["ru_term"].strip().lower()] = row

    glossary_list = list(glossary_map.values())

    cfg = EngineConfig(
        length_overflow_ratio=float(get_setting(db, "length_overflow_ratio", "1.45")),
        button_max_chars=int(get_setting(db, "button_max_chars", "24")),
        latin_check_enabled=get_setting(db, "latin_check_enabled", "true").lower() == "true",
    )

    kk_issues = (
        run_qa_checks(ru_parsed.entries, kk_parsed.entries, lang="kk", glossary=glossary_list, config=cfg)
        if kk_parsed
        else []
    )
    uz_issues = (
        run_qa_checks(ru_parsed.entries, uz_parsed.entries, lang="uz", glossary=glossary_list, config=cfg)
        if uz_parsed
        else []
    )

    all_detected = kk_issues + uz_issues
    llm_used = False

    api_key = get_setting(db, "llm_api_key", "")
    if use_llm and api_key:
        provider = get_setting(db, "llm_provider", "gemini")
        model = get_setting(db, "llm_model", "gemini-2.5-flash")
        base_url = get_setting(db, "llm_base_url", "")
        all_detected, llm_used = enrich_issues_with_llm(
            all_detected,
            glossary=glossary_list,
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
        )

    total_keys = len(ru_parsed.entries)
    checked_strings = total_keys * ((1 if kk_parsed else 0) + (1 if uz_parsed else 0))
    kk_score = compute_quality_score(total_keys, kk_issues) if kk_parsed else 100.0
    uz_score = compute_quality_score(total_keys, uz_issues) if uz_parsed else None

    high_cnt = sum(1 for i in all_detected if i.severity == "high")
    med_cnt = sum(1 for i in all_detected if i.severity == "medium")
    low_cnt = sum(1 for i in all_detected if i.severity == "low")
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    run = ProjectRun(
        name=run_name,
        workspace_token=workspace_token,
        is_demo=is_demo,
        status="completed",
        source_locale=ru_parsed.locale or "ru",
        has_kk=kk_parsed is not None,
        has_uz=uz_parsed is not None,
        has_en=en_parsed is not None,
        total_keys=total_keys,
        checked_strings=checked_strings,
        total_issues=len(all_detected),
        high_issues=high_cnt,
        medium_issues=med_cnt,
        low_issues=low_cnt,
        fixed_count=0,
        human_reviewed_count=0,
        kk_quality_score=kk_score,
        uz_quality_score=uz_score,
        ai_mode_used="hybrid_llm" if llm_used else "rule_engine",
        duration_ms=elapsed_ms,
    )
    db.add(run)
    db.flush()

    # Link files to this run (if not linked yet)
    for uf in (ru_file, kk_file, uz_file, en_file, glossary_file):
        if uf is not None and uf.run_id is None:
            uf.run_id = run.id

    # Fast batch insert of TranslationEntry records (scales smoothly to 5,500+ keys)
    entry_dicts: list[dict] = []
    for lang_code, parsed_target in (("kk", kk_parsed), ("uz", uz_parsed)):
        if parsed_target is None:
            continue
        for key, src_text in ru_parsed.entries.items():
            orig_tgt = parsed_target.entries.get(key, "")
            en_val = en_parsed.entries.get(key) if en_parsed else None
            meta_obj = parsed_target.metadata.get(key) or ru_parsed.metadata.get(key)
            latin_prev = transliterate_kk_to_latin(orig_tgt) if (lang_code == "kk" and orig_tgt) else None
            entry_dicts.append(
                {
                    "run_id": run.id,
                    "lang": lang_code,
                    "key": key,
                    "source_text": src_text,
                    "en_text": en_val,
                    "original_target": orig_tgt,
                    "current_target": orig_tgt,
                    "latin_preview": latin_prev,
                    "metadata_json": json.dumps(meta_obj, ensure_ascii=False) if meta_obj else None,
                    "is_fixed": False,
                    "reviewed_by_human": False,
                    "review_status": "pending",
                }
            )

    if entry_dicts:
        db.execute(insert(TranslationEntry), entry_dicts)
        db.flush()

    # Map (lang, key) -> entry.id for issue foreign keys
    entry_id_rows = db.execute(
        select(TranslationEntry.id, TranslationEntry.lang, TranslationEntry.key).where(
            TranslationEntry.run_id == run.id
        )
    ).all()
    entry_lookup = {(row.lang, row.key): row.id for row in entry_id_rows}

    issue_dicts: list[dict] = []
    for det in all_detected:
        eid = entry_lookup.get((det.lang, det.key))
        if eid is None:
            continue
        issue_dicts.append(
            {
                "run_id": run.id,
                "entry_id": eid,
                "lang": det.lang,
                "key": det.key,
                "issue_type": det.issue_type,
                "severity": det.severity,
                "source": det.source,
                "target": det.target,
                "evidence": det.evidence,
                "suggestion": det.suggestion,
                "confidence": det.confidence,
                "auto_fix_safe": det.auto_fix_safe,
                "reviewed_by_human": False,
                "resolution": "open",
            }
        )

    if issue_dicts:
        db.execute(insert(QAIssue), issue_dicts)

    db.commit()
    db.refresh(run)
    return run


@router.post("/checks/run", response_model=ProjectRunOut)
def create_qa_check_run(
    payload: RunCreateRequest,
    db: Session = Depends(get_db),
    workspace_token: str = Depends(get_workspace_token),
):
    def _fetch_file(fid: int | None, expected_role: str | None = None) -> UploadedFile | None:
        if fid is None:
            return None
        f = db.scalar(
            select(UploadedFile).where(
                UploadedFile.id == fid,
                UploadedFile.workspace_token == workspace_token,
            )
        )
        if not f:
            raise HTTPException(status_code=404, detail=f"Файл (ID={fid}) табылмады.")
        if not f.is_valid:
            raise HTTPException(status_code=400, detail=f"«{f.original_filename}» файлы жарамсыз.")
        return f

    ru_f = _fetch_file(payload.ru_file_id, "ru")
    assert ru_f is not None
    kk_f = _fetch_file(payload.kk_file_id, "kk")
    uz_f = _fetch_file(payload.uz_file_id, "uz")
    en_f = _fetch_file(payload.en_file_id, "en")
    gl_f = _fetch_file(payload.glossary_file_id, "glossary")

    return _execute_qa_pipeline(
        db=db,
        workspace_token=workspace_token,
        run_name=payload.name.strip(),
        is_demo=False,
        ru_file=ru_f,
        kk_file=kk_f,
        uz_file=uz_f,
        en_file=en_f,
        glossary_file=gl_f,
        use_llm=payload.use_llm,
    )


@router.post("/checks/demo", response_model=ProjectRunOut)
def run_demo_qa_check(
    db: Session = Depends(get_db),
    workspace_token: str = Depends(get_workspace_token),
):
    """
    Run a real QA check over the built-in [DEMO] mobile game ARB files.
    Explicitly marked as `is_demo=True` in accordance with specification.
    """
    demo_files_spec = [
        ("ru", "intl_ru.arb"),
        ("kk", "intl_kk.arb"),
        ("uz", "intl_uz.arb"),
        ("en", "intl_en.arb"),
    ]
    created_files: dict[str, UploadedFile] = {}
    for role, fname in demo_files_spec:
        fpath = DEMO_DIR / fname
        if not fpath.exists():
            raise HTTPException(status_code=500, detail=f"DEMO файлы табылмады: {fname}")
        raw_text = fpath.read_text(encoding="utf-8")
        parsed = parse_arb_content(raw_text, fname)
        uf = UploadedFile(
            workspace_token=workspace_token,
            role=role,
            original_filename=f"[DEMO] {fname}",
            stored_path=str(fpath),
            file_format="ARB",
            size_bytes=len(raw_text.encode("utf-8")),
            line_count=parsed.line_count,
            key_count=len(parsed.entries),
            is_valid=True,
            is_demo=True,
            raw_content=raw_text,
        )
        db.add(uf)
        created_files[role] = uf

    db.flush()
    return _execute_qa_pipeline(
        db=db,
        workspace_token=workspace_token,
        run_name="[DEMO] Grand RP Mobile",
        is_demo=True,
        ru_file=created_files["ru"],
        kk_file=created_files["kk"],
        uz_file=created_files["uz"],
        en_file=created_files["en"],
        glossary_file=None,
        use_llm=True,
    )


@router.get("/checks", response_model=list[ProjectRunOut])
def list_qa_runs(
    db: Session = Depends(get_db),
    workspace_token: str = Depends(get_workspace_token),
):
    runs = db.scalars(
        select(ProjectRun)
        .where(ProjectRun.workspace_token == workspace_token)
        .order_by(ProjectRun.created_at.desc())
    ).all()
    return list(runs)


@router.get("/checks/{run_id}", response_model=ProjectRunOut)
def get_qa_run(
    run_id: int,
    db: Session = Depends(get_db),
    workspace_token: str = Depends(get_workspace_token),
):
    run = db.scalar(
        select(ProjectRun).where(
            ProjectRun.id == run_id,
            ProjectRun.workspace_token == workspace_token,
        )
    )
    if not run:
        raise HTTPException(status_code=404, detail="Жоба тексеруі табылмады.")
    return run


@router.delete("/checks/{run_id}")
def delete_qa_run(
    run_id: int,
    db: Session = Depends(get_db),
    workspace_token: str = Depends(get_workspace_token),
):
    run = db.scalar(
        select(ProjectRun).where(
            ProjectRun.id == run_id,
            ProjectRun.workspace_token == workspace_token,
        )
    )
    if not run:
        raise HTTPException(status_code=404, detail="Жоба тексеруі табылмады.")
    for uf in list(run.files):
        if not uf.is_demo and uf.stored_path:
            try:
                p = Path(uf.stored_path)
                if p.exists():
                    p.unlink(missing_ok=True)
                if p.parent.exists() and not any(p.parent.iterdir()):
                    p.parent.rmdir()
            except OSError:
                pass
    db.delete(run)
    db.commit()
    return {"ok": True}


@router.post("/transliterate", response_model=TransliterateOut)
def transliterate_text_endpoint(payload: TransliterateRequest):
    latin = transliterate_kk_to_latin(payload.text)
    max_len = payload.max_length or 24
    return TransliterateOut(
        source_cyrillic=payload.text,
        latin_text=latin,
        cyrillic_length=len(payload.text),
        latin_length=len(latin),
        length_delta=len(latin) - len(payload.text),
        overflow=len(latin) > max_len,
    )
