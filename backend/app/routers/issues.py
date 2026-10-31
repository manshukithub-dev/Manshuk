from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from backend.app.database import get_db
from backend.app.models import ProjectRun, QAIssue, TranslationEntry
from backend.app.routers.deps import (
    get_active_reviewer_name,
    get_workspace_token,
    recalculate_run_stats,
)
from backend.app.schemas import EntryUpdateRequest, IssueActionRequest, IssueOut
from backend.app.services.kazakh_nlp import transliterate_kk_to_latin

router = APIRouter(prefix="/api", tags=["issues"])


def _resolve_active_run(db: Session, workspace_token: str, run_id: int | None) -> ProjectRun | None:
    if run_id is not None:
        return db.scalar(
            select(ProjectRun).where(
                ProjectRun.id == run_id,
                ProjectRun.workspace_token == workspace_token,
            )
        )
    return db.scalar(
        select(ProjectRun)
        .where(ProjectRun.workspace_token == workspace_token)
        .order_by(ProjectRun.created_at.desc())
        .limit(1)
    )


def _serialize_issue(issue: QAIssue) -> IssueOut:
    entry = issue.entry
    return IssueOut(
        id=issue.id,
        run_id=issue.run_id,
        entry_id=issue.entry_id,
        lang=issue.lang,
        key=issue.key,
        issue_type=issue.issue_type,
        severity=issue.severity,
        source=issue.source,
        target=issue.target,
        evidence=issue.evidence,
        suggestion=issue.suggestion,
        confidence=issue.confidence,
        auto_fix_safe=issue.auto_fix_safe,
        reviewed_by_human=issue.reviewed_by_human,
        resolution=issue.resolution,
        resolved_by=issue.resolved_by,
        updated_at=issue.updated_at,
        en_text=entry.en_text if entry else None,
        current_target=entry.current_target if entry else issue.target,
        latin_preview=entry.latin_preview if entry else None,
        entry_review_status=entry.review_status if entry else None,
    )


@router.get("/issues")
def list_issues(
    run_id: int | None = Query(default=None),
    severity: str | None = Query(default=None),
    lang: str | None = Query(default=None),
    issue_type: str | None = Query(default=None),
    reviewed: str | None = Query(default=None),  # "true" | "false" | None
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    workspace_token: str = Depends(get_workspace_token),
):
    run = _resolve_active_run(db, workspace_token, run_id)
    if not run:
        return {"run_id": None, "total": 0, "page": page, "page_size": page_size, "items": []}

    stmt = (
        select(QAIssue)
        .options(joinedload(QAIssue.entry))
        .where(QAIssue.run_id == run.id)
    )
    count_stmt = select(func.count(QAIssue.id)).where(QAIssue.run_id == run.id)

    if severity and severity != "all":
        stmt = stmt.where(QAIssue.severity == severity.lower())
        count_stmt = count_stmt.where(QAIssue.severity == severity.lower())
    if lang and lang != "all":
        stmt = stmt.where(QAIssue.lang == lang.lower())
        count_stmt = count_stmt.where(QAIssue.lang == lang.lower())
    if issue_type and issue_type != "all":
        stmt = stmt.where(QAIssue.issue_type == issue_type)
        count_stmt = count_stmt.where(QAIssue.issue_type == issue_type)
    if reviewed == "true":
        stmt = stmt.where(QAIssue.reviewed_by_human.is_(True))
        count_stmt = count_stmt.where(QAIssue.reviewed_by_human.is_(True))
    elif reviewed == "false":
        stmt = stmt.where(QAIssue.reviewed_by_human.is_(False))
        count_stmt = count_stmt.where(QAIssue.reviewed_by_human.is_(False))

    if search and search.strip():
        q = f"%{search.strip()}%"
        cond = or_(
            QAIssue.key.ilike(q),
            QAIssue.source.ilike(q),
            QAIssue.target.ilike(q),
            QAIssue.suggestion.ilike(q),
            QAIssue.evidence.ilike(q),
        )
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    total = db.scalar(count_stmt) or 0
    rows = db.scalars(
        stmt.order_by(QAIssue.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "run_id": run.id,
        "run_name": run.name,
        "is_demo": run.is_demo,
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize_issue(r) for r in rows],
    }


@router.post("/issues/{issue_id}/action", response_model=IssueOut)
def apply_issue_action(
    issue_id: int,
    payload: IssueActionRequest,
    db: Session = Depends(get_db),
    workspace_token: str = Depends(get_workspace_token),
):
    issue = db.scalar(
        select(QAIssue)
        .options(joinedload(QAIssue.entry), joinedload(QAIssue.run))
        .where(QAIssue.id == issue_id)
    )
    if not issue or not issue.run or issue.run.workspace_token != workspace_token:
        raise HTTPException(status_code=404, detail="Қате жазбасы табылмады.")

    entry = issue.entry
    reviewer = (payload.reviewer_name or "").strip() or get_active_reviewer_name(db)
    now = datetime.now(timezone.utc)
    act = payload.action.strip().lower()

    if act == "accept_suggestion":
        if not issue.suggestion:
            raise HTTPException(status_code=400, detail="Бұл қате үшін дайын AI ұсынысы жоқ; қолмен өзгертіңіз.")
        entry.current_target = issue.suggestion
        entry.is_fixed = True
        entry.reviewed_by_human = True
        entry.reviewer_name = reviewer
        entry.reviewed_at = now
        entry.review_status = "approved"
        if entry.lang == "kk":
            entry.latin_preview = transliterate_kk_to_latin(entry.current_target)

        issue.target = entry.current_target
        issue.reviewed_by_human = True
        issue.resolution = "accepted"
        issue.resolved_by = reviewer
        issue.updated_at = now

    elif act == "manual_edit":
        if payload.new_target is None or not payload.new_target.strip():
            raise HTTPException(status_code=400, detail="Жаңа аударма мәтіні бос болмауы тиіс.")
        entry.current_target = payload.new_target
        entry.is_fixed = entry.current_target != entry.original_target
        entry.reviewed_by_human = True
        entry.reviewer_name = reviewer
        entry.reviewed_at = now
        entry.review_status = "approved"
        if entry.lang == "kk":
            entry.latin_preview = transliterate_kk_to_latin(entry.current_target)

        issue.target = entry.current_target
        issue.reviewed_by_human = True
        issue.resolution = "manual_edit"
        issue.resolved_by = reviewer
        issue.updated_at = now

    elif act == "mark_reviewed":
        if payload.new_target is not None and payload.new_target.strip():
            entry.current_target = payload.new_target
            entry.is_fixed = entry.current_target != entry.original_target
            if entry.lang == "kk":
                entry.latin_preview = transliterate_kk_to_latin(entry.current_target)
            issue.target = entry.current_target
        entry.reviewed_by_human = True
        entry.reviewer_name = reviewer
        entry.reviewed_at = now
        entry.review_status = "approved"

        issue.reviewed_by_human = True
        issue.resolution = "reviewed_ok"
        issue.resolved_by = reviewer
        issue.updated_at = now

    elif act == "reject_suggestion":
        entry.current_target = entry.original_target
        entry.is_fixed = False
        entry.reviewed_by_human = True
        entry.reviewer_name = reviewer
        entry.reviewed_at = now
        entry.review_status = "rejected"
        if entry.lang == "kk":
            entry.latin_preview = transliterate_kk_to_latin(entry.current_target)

        issue.target = entry.current_target
        issue.reviewed_by_human = True
        issue.resolution = "rejected"
        issue.resolved_by = reviewer
        issue.updated_at = now

    elif act == "auto_apply":
        # Section 8 & Section 10: dangerous auto-fixes are blocked, and auto-fixes keep reviewed_by_human = False!
        if not issue.auto_fix_safe:
            raise HTTPException(
                status_code=400,
                detail="Бұл жолда қауіпті автоматты түзетуге тыйым салынған (мысалы, динамикалық плейсхолдер жалғауы). Маманның қолмен тексеруі қажет.",
            )
        if not issue.suggestion:
            raise HTTPException(status_code=400, detail="Автоматты түзету ұсынысы жоқ.")
        entry.current_target = issue.suggestion
        entry.is_fixed = True
        entry.reviewed_by_human = False
        entry.review_status = "auto_fixed"
        if entry.lang == "kk":
            entry.latin_preview = transliterate_kk_to_latin(entry.current_target)

        issue.target = entry.current_target
        issue.reviewed_by_human = False
        issue.resolution = "auto_applied"
        issue.updated_at = now
    else:
        raise HTTPException(status_code=400, detail=f"Белгісіз әрекет: {act}")

    # Sync sibling issues on the same entry if human reviewed
    if issue.reviewed_by_human:
        siblings = db.scalars(
            select(QAIssue).where(QAIssue.entry_id == entry.id, QAIssue.id != issue.id)
        ).all()
        for sib in siblings:
            sib.target = entry.current_target
            sib.reviewed_by_human = True
            if sib.resolution == "open":
                sib.resolution = "reviewed_ok"
            sib.resolved_by = reviewer
            sib.updated_at = now

    db.flush()
    recalculate_run_stats(db, issue.run)
    db.refresh(issue)
    return _serialize_issue(issue)


@router.post("/issues/batch-auto-fix")
def batch_auto_fix_safe_issues(
    run_id: int = Query(...),
    lang: str | None = Query(default=None),
    db: Session = Depends(get_db),
    workspace_token: str = Depends(get_workspace_token),
):
    """
    Apply safe automatic suggestions WITHOUT marking `reviewed_by_human = True`.
    Dynamic suffix harmony & structural ICU issues (`auto_fix_safe == False`) are skipped!
    """
    run = _resolve_active_run(db, workspace_token, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Жоба табылмады.")

    stmt = (
        select(QAIssue)
        .options(joinedload(QAIssue.entry))
        .where(
            QAIssue.run_id == run.id,
            QAIssue.auto_fix_safe.is_(True),
            QAIssue.reviewed_by_human.is_(False),
            QAIssue.resolution == "open",
        )
    )
    if lang and lang != "all":
        stmt = stmt.where(QAIssue.lang == lang.lower())

    safe_issues = db.scalars(stmt).all()
    applied = 0
    for iss in safe_issues:
        if not iss.suggestion or not iss.entry:
            continue
        iss.entry.current_target = iss.suggestion
        iss.entry.is_fixed = True
        iss.entry.reviewed_by_human = False
        iss.entry.review_status = "auto_fixed"
        if iss.entry.lang == "kk":
            iss.entry.latin_preview = transliterate_kk_to_latin(iss.entry.current_target)
        iss.target = iss.suggestion
        iss.reviewed_by_human = False
        iss.resolution = "auto_applied"
        applied += 1

    db.flush()
    recalculate_run_stats(db, run)
    return {"applied_count": applied, "reviewed_by_human": False}


@router.get("/entries")
def list_translation_entries(
    run_id: int | None = Query(default=None),
    lang: str = Query(default="kk"),
    filter_mode: str = Query(default="all"),  # all | with_issues | unreviewed | reviewed | auto_fixed
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    workspace_token: str = Depends(get_workspace_token),
):
    run = _resolve_active_run(db, workspace_token, run_id)
    if not run:
        return {"run_id": None, "total": 0, "items": []}

    stmt = (
        select(TranslationEntry)
        .options(joinedload(TranslationEntry.issues))
        .where(TranslationEntry.run_id == run.id, TranslationEntry.lang == lang.lower())
    )
    count_stmt = select(func.count(TranslationEntry.id)).where(
        TranslationEntry.run_id == run.id, TranslationEntry.lang == lang.lower()
    )

    if filter_mode == "unreviewed":
        stmt = stmt.where(TranslationEntry.reviewed_by_human.is_(False))
        count_stmt = count_stmt.where(TranslationEntry.reviewed_by_human.is_(False))
    elif filter_mode == "reviewed":
        stmt = stmt.where(TranslationEntry.reviewed_by_human.is_(True))
        count_stmt = count_stmt.where(TranslationEntry.reviewed_by_human.is_(True))
    elif filter_mode == "auto_fixed":
        stmt = stmt.where(TranslationEntry.review_status == "auto_fixed")
        count_stmt = count_stmt.where(TranslationEntry.review_status == "auto_fixed")
    elif filter_mode == "with_issues":
        stmt = stmt.where(TranslationEntry.issues.any())
        count_stmt = count_stmt.where(TranslationEntry.issues.any())

    if search and search.strip():
        q = f"%{search.strip()}%"
        cond = or_(
            TranslationEntry.key.ilike(q),
            TranslationEntry.source_text.ilike(q),
            TranslationEntry.current_target.ilike(q),
        )
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    total = db.scalar(count_stmt) or 0
    entries = db.scalars(
        stmt.order_by(TranslationEntry.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).unique().all()

    items = [
        {
            "id": e.id,
            "run_id": e.run_id,
            "lang": e.lang,
            "key": e.key,
            "source_text": e.source_text,
            "en_text": e.en_text,
            "original_target": e.original_target,
            "current_target": e.current_target,
            "latin_preview": e.latin_preview,
            "is_fixed": e.is_fixed,
            "reviewed_by_human": e.reviewed_by_human,
            "reviewer_name": e.reviewer_name,
            "review_status": e.review_status,
            "issues": [_serialize_issue(iss) for iss in e.issues],
        }
        for e in entries
    ]
    return {
        "run_id": run.id,
        "run_name": run.name,
        "is_demo": run.is_demo,
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


@router.put("/entries/{entry_id}")
def update_translation_entry(
    entry_id: int,
    payload: EntryUpdateRequest,
    db: Session = Depends(get_db),
    workspace_token: str = Depends(get_workspace_token),
):
    entry = db.scalar(
        select(TranslationEntry)
        .options(joinedload(TranslationEntry.run), joinedload(TranslationEntry.issues))
        .where(TranslationEntry.id == entry_id)
    )
    if not entry or not entry.run or entry.run.workspace_token != workspace_token:
        raise HTTPException(status_code=404, detail="Жол табылмады.")

    reviewer = (payload.reviewer_name or "").strip() or get_active_reviewer_name(db)
    now = datetime.now(timezone.utc)

    entry.current_target = payload.current_target
    entry.is_fixed = entry.current_target != entry.original_target
    entry.reviewed_by_human = payload.reviewed_by_human
    if payload.reviewed_by_human:
        entry.reviewer_name = reviewer
        entry.reviewed_at = now
        entry.review_status = "approved"
    else:
        entry.review_status = "auto_fixed" if entry.is_fixed else "pending"

    if entry.lang == "kk":
        entry.latin_preview = transliterate_kk_to_latin(entry.current_target)

    for iss in entry.issues:
        iss.target = entry.current_target
        iss.reviewed_by_human = payload.reviewed_by_human
        if payload.reviewed_by_human:
            iss.resolution = "manual_edit" if entry.is_fixed else "reviewed_ok"
            iss.resolved_by = reviewer
        iss.updated_at = now

    db.flush()
    recalculate_run_stats(db, entry.run)
    return {
        "id": entry.id,
        "key": entry.key,
        "current_target": entry.current_target,
        "latin_preview": entry.latin_preview,
        "is_fixed": entry.is_fixed,
        "reviewed_by_human": entry.reviewed_by_human,
        "review_status": entry.review_status,
    }
