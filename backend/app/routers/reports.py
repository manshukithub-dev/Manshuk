from __future__ import annotations

from collections import Counter
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import ProjectRun, QAIssue, TranslationEntry, UploadedFile
from backend.app.routers.deps import get_workspace_token
from backend.app.services.arb_parser import ARBValidationError, export_fixed_arb
from backend.app.services.report_service import (
    ISSUE_TYPE_LABELS_KK,
    format_issue_json_item,
    generate_html_report,
    generate_json_report,
    generate_recommendations,
)

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _get_run_or_404(db: Session, run_id: int, workspace_token: str) -> ProjectRun:
    run = db.scalar(
        select(ProjectRun).where(
            ProjectRun.id == run_id,
            ProjectRun.workspace_token == workspace_token,
        )
    )
    if not run:
        raise HTTPException(status_code=404, detail="Жоба тексеруі табылмады.")
    return run


@router.get("/{run_id}/summary")
def get_report_summary(
    run_id: int,
    lang: str | None = Query(default=None),
    db: Session = Depends(get_db),
    workspace_token: str = Depends(get_workspace_token),
):
    run = _get_run_or_404(db, run_id, workspace_token)
    issue_stmt = select(QAIssue).where(QAIssue.run_id == run.id)
    if lang and lang != "all":
        issue_stmt = issue_stmt.where(QAIssue.lang == lang.lower())
    issues = list(db.scalars(issue_stmt.order_by(QAIssue.id.asc())).all())

    fixed_cnt = db.scalar(
        select(func.count(TranslationEntry.id)).where(
            TranslationEntry.run_id == run.id,
            TranslationEntry.is_fixed.is_(True),
        )
    ) or 0
    human_cnt = db.scalar(
        select(func.count(TranslationEntry.id)).where(
            TranslationEntry.run_id == run.id,
            TranslationEntry.reviewed_by_human.is_(True),
        )
    ) or 0
    unreviewed_cnt = max(0, run.checked_strings - human_cnt)

    type_counts = Counter(i.issue_type for i in issues)
    sev_counts = Counter(i.severity for i in issues)
    recs = generate_recommendations(type_counts, unreviewed_cnt)

    return {
        "run_id": run.id,
        "project_name": run.name,
        "is_demo": run.is_demo,
        "has_kk": run.has_kk,
        "has_uz": run.has_uz,
        "total_strings": run.checked_strings,
        "total_keys": run.total_keys,
        "total_issues": len(issues),
        "severity_stats": {
            "high": sev_counts.get("high", 0),
            "medium": sev_counts.get("medium", 0),
            "low": sev_counts.get("low", 0),
        },
        "issue_types": [
            {
                "issue_type": k,
                "label": ISSUE_TYPE_LABELS_KK.get(k, k),
                "count": v,
            }
            for k, v in type_counts.most_common()
        ],
        "fixed_strings": fixed_cnt,
        "human_reviewed_strings": human_cnt,
        "unreviewed_strings": unreviewed_cnt,
        "kk_quality_score": run.kk_quality_score,
        "uz_quality_score": run.uz_quality_score,
        "recommendations": recs,
        "sample_json": [format_issue_json_item(i) for i in issues[:10]],
    }


@router.get("/{run_id}/json")
def download_json_report(
    run_id: int,
    lang: str | None = Query(default=None),
    db: Session = Depends(get_db),
    workspace_token: str = Depends(get_workspace_token),
):
    run = _get_run_or_404(db, run_id, workspace_token)
    stmt = select(QAIssue).where(QAIssue.run_id == run.id)
    if lang and lang != "all":
        stmt = stmt.where(QAIssue.lang == lang.lower())
    issues = list(db.scalars(stmt.order_by(QAIssue.id.asc())).all())
    json_content = generate_json_report(issues, include_wrapper=False)
    suffix = f"_{lang}" if lang and lang != "all" else ""
    return Response(
        content=json_content,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="qazaq_locqa_report_{run.id}{suffix}.json"'},
    )


@router.get("/{run_id}/html")
def download_html_report(
    run_id: int,
    lang: str | None = Query(default=None),
    download: bool = Query(default=True),
    db: Session = Depends(get_db),
    workspace_token: str = Depends(get_workspace_token),
):
    run = _get_run_or_404(db, run_id, workspace_token)
    stmt = select(QAIssue).where(QAIssue.run_id == run.id)
    if lang and lang != "all":
        stmt = stmt.where(QAIssue.lang == lang.lower())
    issues = list(db.scalars(stmt.order_by(QAIssue.id.asc())).all())
    fixed_cnt = db.scalar(
        select(func.count(TranslationEntry.id)).where(
            TranslationEntry.run_id == run.id, TranslationEntry.is_fixed.is_(True)
        )
    ) or 0
    human_cnt = db.scalar(
        select(func.count(TranslationEntry.id)).where(
            TranslationEntry.run_id == run.id, TranslationEntry.reviewed_by_human.is_(True)
        )
    ) or 0
    unreviewed_cnt = max(0, run.checked_strings - human_cnt)

    html_doc = generate_html_report(
        project_name=run.name,
        total_strings=run.checked_strings,
        fixed_strings=fixed_cnt,
        human_reviewed_strings=human_cnt,
        unreviewed_strings=unreviewed_cnt,
        kk_score=run.kk_quality_score,
        uz_score=run.uz_quality_score,
        issues=issues,
        is_demo=run.is_demo,
    )
    if not download:
        return HTMLResponse(content=html_doc)
    return Response(
        content=html_doc,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="qazaq_locqa_report_{run.id}.html"'},
    )


@router.get("/{run_id}/export-arb")
def export_fixed_arb_endpoint(
    run_id: int,
    lang: str = Query(default="kk"),
    only_human_verified: bool = Query(default=False),
    db: Session = Depends(get_db),
    workspace_token: str = Depends(get_workspace_token),
):
    """
    Export validated Flutter gen-l10n compliant ARB (`intl_kk_fixed.arb` or `intl_uz_fixed.arb`).
    Preserves original key order, @metadata, ICU syntax, and marks human-verified entries via `x-reviewed-by-human`.
    When `only_human_verified=True`, only human-approved edits are applied (unreviewed auto-fixes keep original target).
    """
    run = _get_run_or_404(db, run_id, workspace_token)
    lang_code = lang.strip().lower()
    if lang_code not in ("kk", "uz"):
        raise HTTPException(status_code=400, detail="Тіл тек 'kk' немесе 'uz' болуы керек.")

    files = list(db.scalars(select(UploadedFile).where(UploadedFile.run_id == run.id)).all())
    ru_file = next((f for f in files if f.role == "ru"), None)
    tgt_file = next((f for f in files if f.role == lang_code), None)

    if not ru_file or not ru_file.raw_content:
        raise HTTPException(status_code=404, detail="Бастапқы орысша ARB файлы табылмады.")

    entries = list(
        db.scalars(
            select(TranslationEntry).where(
                TranslationEntry.run_id == run.id,
                TranslationEntry.lang == lang_code,
            )
        ).all()
    )
    if not entries:
        raise HTTPException(status_code=404, detail=f"«{lang_code}» тілі бойынша аударма жолдары жоқ.")

    updates_map = {}
    for e in entries:
        chosen_target = (
            e.current_target
            if (not only_human_verified or e.reviewed_by_human)
            else e.original_target
        )
        updates_map[e.key] = {
            "current_target": chosen_target,
            "is_fixed": chosen_target != e.original_target,
            "reviewed_by_human": e.reviewed_by_human,
            "reviewer_name": e.reviewer_name,
            "reviewed_at": e.reviewed_at.isoformat() if e.reviewed_at else None,
        }

    try:
        arb_json, summary, _warnings = export_fixed_arb(
            original_target_raw=tgt_file.raw_content if tgt_file else None,
            source_raw=ru_file.raw_content,
            updated_entries=updates_map,
            target_locale=lang_code,
        )
    except ARBValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    out_filename = f"intl_{lang_code}_fixed.arb"
    return Response(
        content=arb_json,
        media_type="application/json; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{out_filename}"',
            "X-LocQA-Modified-Keys": str(summary["modified_keys"]),
            "X-LocQA-Human-Verified": str(summary["human_verified_keys"]),
        },
    )
