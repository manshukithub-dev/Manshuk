from __future__ import annotations

from collections import Counter
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import ProjectRun, QAIssue, TranslationEntry
from backend.app.routers.deps import get_workspace_token
from backend.app.schemas import DashboardStatsOut, ProjectRunOut
from backend.app.services.report_service import ISSUE_TYPE_LABELS_KK

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardStatsOut)
def get_dashboard_stats(
    run_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    workspace_token: str = Depends(get_workspace_token),
):
    runs = list(
        db.scalars(
            select(ProjectRun)
            .where(ProjectRun.workspace_token == workspace_token)
            .order_by(ProjectRun.created_at.desc())
        ).all()
    )
    if not runs:
        return DashboardStatsOut(
            has_runs=False,
            active_run=None,
            total_runs_count=0,
            total_checked_strings=0,
            total_issues=0,
            high_severity_issues=0,
            medium_severity_issues=0,
            low_severity_issues=0,
            fixed_strings=0,
            human_reviewed_strings=0,
            unreviewed_strings=0,
            kk_quality_score=0.0,
            uz_quality_score=None,
            issues_by_type=[],
            severity_breakdown=[],
            runs_trend=[],
            language_comparison=[],
            recent_runs=[],
        )

    active = next((r for r in runs if r.id == run_id), runs[0])

    # Compute exact live metrics for the active run (or aggregate across runs where appropriate)
    total_checked = active.checked_strings
    issues = list(db.scalars(select(QAIssue).where(QAIssue.run_id == active.id)).all())

    fixed_strings = db.scalar(
        select(func.count(TranslationEntry.id)).where(
            TranslationEntry.run_id == active.id,
            TranslationEntry.is_fixed.is_(True),
        )
    ) or 0

    human_reviewed = db.scalar(
        select(func.count(TranslationEntry.id)).where(
            TranslationEntry.run_id == active.id,
            TranslationEntry.reviewed_by_human.is_(True),
        )
    ) or 0

    unreviewed = max(0, total_checked - human_reviewed)

    type_counter = Counter(i.issue_type for i in issues)
    issues_by_type = [
        {
            "issue_type": itype,
            "label": ISSUE_TYPE_LABELS_KK.get(itype, itype).split(" (")[0],
            "count": cnt,
        }
        for itype, cnt in type_counter.most_common()
    ]

    sev_counter = Counter(i.severity for i in issues)
    severity_breakdown = [
        {"severity": "High", "count": sev_counter.get("high", 0), "color": "#f43f5e"},
        {"severity": "Medium", "count": sev_counter.get("medium", 0), "color": "#f59e0b"},
        {"severity": "Low", "count": sev_counter.get("low", 0), "color": "#38bdf8"},
    ]

    # Trend across chronological runs (up to last 10 runs)
    chronological = list(reversed(runs[:10]))
    runs_trend = [
        {
            "id": r.id,
            "name": (r.name[:18] + "…") if len(r.name) > 18 else r.name,
            "kk_score": r.kk_quality_score,
            "uz_score": r.uz_quality_score if r.uz_quality_score is not None else 0,
            "issues": r.total_issues,
            "reviewed": r.human_reviewed_count,
            "is_demo": r.is_demo,
        }
        for r in chronological
    ]

    kk_issues_cnt = sum(1 for i in issues if i.lang == "kk")
    uz_issues_cnt = sum(1 for i in issues if i.lang == "uz")
    kk_reviewed_cnt = db.scalar(
        select(func.count(TranslationEntry.id)).where(
            TranslationEntry.run_id == active.id,
            TranslationEntry.lang == "kk",
            TranslationEntry.reviewed_by_human.is_(True),
        )
    ) or 0
    uz_reviewed_cnt = db.scalar(
        select(func.count(TranslationEntry.id)).where(
            TranslationEntry.run_id == active.id,
            TranslationEntry.lang == "uz",
            TranslationEntry.reviewed_by_human.is_(True),
        )
    ) or 0

    language_comparison = []
    if active.has_kk:
        language_comparison.append(
            {
                "language": "Қазақша (KK)",
                "score": active.kk_quality_score,
                "issues": kk_issues_cnt,
                "reviewed": kk_reviewed_cnt,
                "total": active.total_keys,
            }
        )
    if active.has_uz and active.uz_quality_score is not None:
        language_comparison.append(
            {
                "language": "Өзбекше (UZ)",
                "score": active.uz_quality_score,
                "issues": uz_issues_cnt,
                "reviewed": uz_reviewed_cnt,
                "total": active.total_keys,
            }
        )

    return DashboardStatsOut(
        has_runs=True,
        active_run=ProjectRunOut.model_validate(active),
        total_runs_count=len(runs),
        total_checked_strings=total_checked,
        total_issues=len(issues),
        high_severity_issues=sev_counter.get("high", 0),
        medium_severity_issues=sev_counter.get("medium", 0),
        low_severity_issues=sev_counter.get("low", 0),
        fixed_strings=fixed_strings,
        human_reviewed_strings=human_reviewed,
        unreviewed_strings=unreviewed,
        kk_quality_score=active.kk_quality_score,
        uz_quality_score=active.uz_quality_score,
        issues_by_type=issues_by_type,
        severity_breakdown=severity_breakdown,
        runs_trend=runs_trend,
        language_comparison=language_comparison,
        recent_runs=[ProjectRunOut.model_validate(r) for r in runs[:8]],
    )
