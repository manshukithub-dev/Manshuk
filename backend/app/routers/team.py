from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import TeamMember, TranslationEntry
from backend.app.schemas import TeamMemberIn, TeamMemberOut

router = APIRouter(prefix="/api/team", tags=["team"])

DEFAULT_TEAM_MEMBERS = [
    {
        "name": "Айгерім Сейітова",
        "role": "Қазақ тілінің бас лингвист-редакторы",
        "languages": "KK, RU, EN",
        "email": "aigerim.qa@qazaqloc.kz",
        "avatar_initials": "АС",
        "is_active_reviewer": True,
    },
    {
        "name": "Нұрлан Бекболат",
        "role": "Senior Localization QA Engineer",
        "languages": "KK, RU, EN",
        "email": "nurlan.qa@qazaqloc.kz",
        "avatar_initials": "НБ",
        "is_active_reviewer": False,
    },
    {
        "name": "Сардор Кәрімов",
        "role": "Өзбек локализациясының сарапшысы",
        "languages": "UZ, RU, EN",
        "email": "sardor.uz@qazaqloc.kz",
        "avatar_initials": "СК",
        "is_active_reviewer": False,
    },
    {
        "name": "Дархан Әлиев",
        "role": "Flutter / Mobile Game интеграция инженері",
        "languages": "KK, EN",
        "email": "darkhan.dev@qazaqloc.kz",
        "avatar_initials": "ДӘ",
        "is_active_reviewer": False,
    },
]


def seed_default_team(db: Session) -> None:
    exists = db.scalar(select(TeamMember.id).limit(1))
    if exists is not None:
        return
    for item in DEFAULT_TEAM_MEMBERS:
        db.add(TeamMember(**item))
    db.commit()


def _make_initials(name: str) -> str:
    parts = [p for p in name.strip().split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return (name.strip()[:2] or "QA").upper()


@router.get("", response_model=list[TeamMemberOut])
def list_team_members(db: Session = Depends(get_db)):
    members = list(db.scalars(select(TeamMember).order_by(TeamMember.id.asc())).all())
    review_counts = dict(
        db.execute(
            select(TranslationEntry.reviewer_name, func.count(TranslationEntry.id))
            .where(TranslationEntry.reviewed_by_human.is_(True))
            .group_by(TranslationEntry.reviewer_name)
        ).all()
    )
    out: list[TeamMemberOut] = []
    for m in members:
        out.append(
            TeamMemberOut(
                id=m.id,
                name=m.name,
                role=m.role,
                languages=m.languages,
                email=m.email,
                is_active_reviewer=m.is_active_reviewer,
                avatar_initials=m.avatar_initials,
                reviewed_count=int(review_counts.get(m.name, 0)),
                created_at=m.created_at,
            )
        )
    return out


@router.post("", response_model=TeamMemberOut)
def create_team_member(payload: TeamMemberIn, db: Session = Depends(get_db)):
    if payload.is_active_reviewer:
        for existing in db.scalars(select(TeamMember)).all():
            existing.is_active_reviewer = False

    member = TeamMember(
        name=payload.name.strip(),
        role=payload.role.strip(),
        languages=payload.languages.strip(),
        email=payload.email.strip(),
        avatar_initials=_make_initials(payload.name),
        is_active_reviewer=payload.is_active_reviewer,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return TeamMemberOut(
        id=member.id,
        name=member.name,
        role=member.role,
        languages=member.languages,
        email=member.email,
        is_active_reviewer=member.is_active_reviewer,
        avatar_initials=member.avatar_initials,
        reviewed_count=0,
        created_at=member.created_at,
    )


@router.post("/{member_id}/activate", response_model=TeamMemberOut)
def set_active_reviewer(member_id: int, db: Session = Depends(get_db)):
    target = db.get(TeamMember, member_id)
    if not target:
        raise HTTPException(status_code=404, detail="Команда мүшесі табылмады.")
    for m in db.scalars(select(TeamMember)).all():
        m.is_active_reviewer = m.id == member_id
    db.commit()
    db.refresh(target)
    cnt = db.scalar(
        select(func.count(TranslationEntry.id)).where(
            TranslationEntry.reviewed_by_human.is_(True),
            TranslationEntry.reviewer_name == target.name,
        )
    ) or 0
    return TeamMemberOut(
        id=target.id,
        name=target.name,
        role=target.role,
        languages=target.languages,
        email=target.email,
        is_active_reviewer=target.is_active_reviewer,
        avatar_initials=target.avatar_initials,
        reviewed_count=cnt,
        created_at=target.created_at,
    )


@router.delete("/{member_id}")
def delete_team_member(member_id: int, db: Session = Depends(get_db)):
    target = db.get(TeamMember, member_id)
    if not target:
        raise HTTPException(status_code=404, detail="Команда мүшесі табылмады.")
    was_active = target.is_active_reviewer
    db.delete(target)
    db.commit()
    if was_active:
        first = db.scalar(select(TeamMember).order_by(TeamMember.id.asc()).limit(1))
        if first:
            first.is_active_reviewer = True
            db.commit()
    return {"ok": True}
