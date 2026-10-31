from __future__ import annotations

import re
from fastapi import Header
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import ProjectRun, QAIssue, TeamMember, TranslationEntry

TOKEN_RE = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")


def get_workspace_token(x_workspace_id: str | None = Header(default="default-local")) -> str:
    if not x_workspace_id or not TOKEN_RE.match(x_workspace_id):
        return "default-local"
    return x_workspace_id


def get_active_reviewer_name(db: Session) -> str:
    member = db.scalar(select(TeamMember).where(TeamMember.is_active_reviewer.is_(True)).limit(1))
    if member:
        return member.name
    first = db.scalar(select(TeamMember).limit(1))
    return first.name if first else "Локализация маманы"


def recalculate_run_stats(db: Session, run: ProjectRun) -> None:
    """Recompute run metrics accurately from database entries and issues."""
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

    open_issues = list(
        db.scalars(
            select(QAIssue).where(
                QAIssue.run_id == run.id,
                QAIssue.resolution == "open",
            )
        ).all()
    )
    all_issues_cnt = db.scalar(
        select(func.count(QAIssue.id)).where(QAIssue.run_id == run.id)
    ) or 0
    high_cnt = db.scalar(
        select(func.count(QAIssue.id)).where(QAIssue.run_id == run.id, QAIssue.severity == "high")
    ) or 0
    med_cnt = db.scalar(
        select(func.count(QAIssue.id)).where(QAIssue.run_id == run.id, QAIssue.severity == "medium")
    ) or 0
    low_cnt = db.scalar(
        select(func.count(QAIssue.id)).where(QAIssue.run_id == run.id, QAIssue.severity == "low")
    ) or 0

    run.fixed_count = fixed_cnt
    run.human_reviewed_count = human_cnt
    run.total_issues = all_issues_cnt
    run.high_issues = high_cnt
    run.medium_issues = med_cnt
    run.low_issues = low_cnt

    # Recompute live quality score based on remaining open issues!
    if run.has_kk and run.total_keys > 0:
        kk_open = [i for i in open_issues if i.lang == "kk"]
        penalty_kk = sum(1.0 if i.severity == "high" else (0.55 if i.severity == "medium" else 0.25) for i in kk_open)
        run.kk_quality_score = round(max(0.0, 100.0 * (1.0 - penalty_kk / max(run.total_keys * 1.15, 1.0))), 1)

    if run.has_uz and run.total_keys > 0:
        uz_open = [i for i in open_issues if i.lang == "uz"]
        penalty_uz = sum(1.0 if i.severity == "high" else (0.55 if i.severity == "medium" else 0.25) for i in uz_open)
        run.uz_quality_score = round(max(0.0, 100.0 * (1.0 - penalty_uz / max(run.total_keys * 1.15, 1.0))), 1)

    db.commit()
    db.refresh(run)
