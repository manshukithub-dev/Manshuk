from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProjectRun(Base):
    __tablename__ = "project_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    workspace_token: Mapped[str] = mapped_column(String(128), index=True, default="default-local")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    source_locale: Mapped[str] = mapped_column(String(16), default="ru")
    has_kk: Mapped[bool] = mapped_column(Boolean, default=True)
    has_uz: Mapped[bool] = mapped_column(Boolean, default=False)
    has_en: Mapped[bool] = mapped_column(Boolean, default=False)

    total_keys: Mapped[int] = mapped_column(Integer, default=0)
    checked_strings: Mapped[int] = mapped_column(Integer, default=0)
    total_issues: Mapped[int] = mapped_column(Integer, default=0)
    high_issues: Mapped[int] = mapped_column(Integer, default=0)
    medium_issues: Mapped[int] = mapped_column(Integer, default=0)
    low_issues: Mapped[int] = mapped_column(Integer, default=0)
    fixed_count: Mapped[int] = mapped_column(Integer, default=0)
    human_reviewed_count: Mapped[int] = mapped_column(Integer, default=0)

    kk_quality_score: Mapped[float] = mapped_column(Float, default=100.0)
    uz_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_mode_used: Mapped[str] = mapped_column(String(64), default="rule_engine")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    files: Mapped[list["UploadedFile"]] = relationship(
        "UploadedFile", back_populates="run", cascade="all, delete-orphan"
    )
    entries: Mapped[list["TranslationEntry"]] = relationship(
        "TranslationEntry", back_populates="run", cascade="all, delete-orphan"
    )
    issues: Mapped[list["QAIssue"]] = relationship(
        "QAIssue", back_populates="run", cascade="all, delete-orphan"
    )


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("project_runs.id", ondelete="CASCADE"), nullable=True, index=True
    )
    workspace_token: Mapped[str] = mapped_column(String(128), index=True, default="default-local")
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # ru, kk, uz, en, glossary
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_format: Mapped[str] = mapped_column(String(16), nullable=False)  # ARB or CSV
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    line_count: Mapped[int] = mapped_column(Integer, default=0)
    key_count: Mapped[int] = mapped_column(Integer, default=0)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    validation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped["ProjectRun | None"] = relationship("ProjectRun", back_populates="files")


class TranslationEntry(Base):
    __tablename__ = "translation_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lang: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # kk or uz
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_text: Mapped[str] = mapped_column(Text, default="")
    en_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_target: Mapped[str] = mapped_column(Text, default="")
    current_target: Mapped[str] = mapped_column(Text, default="")
    latin_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_fixed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by_human: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    reviewer_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_status: Mapped[str] = mapped_column(String(32), default="pending")

    run: Mapped["ProjectRun"] = relationship("ProjectRun", back_populates="entries")
    issues: Mapped[list["QAIssue"]] = relationship(
        "QAIssue", back_populates="entry", cascade="all, delete-orphan"
    )


class QAIssue(Base):
    __tablename__ = "qa_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("translation_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lang: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    issue_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # high, medium, low
    source: Mapped[str] = mapped_column(Text, default="")
    target: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[str] = mapped_column(Text, default="")
    suggestion: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.9)
    auto_fix_safe: Mapped[bool] = mapped_column(Boolean, default=True)
    reviewed_by_human: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    resolution: Mapped[str] = mapped_column(String(32), default="open")
    resolved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped["ProjectRun"] = relationship("ProjectRun", back_populates="issues")
    entry: Mapped["TranslationEntry"] = relationship("TranslationEntry", back_populates="issues")


class GlossaryTerm(Base):
    __tablename__ = "glossary_terms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ru_term: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    kk_term: Mapped[str] = mapped_column(String(255), nullable=False)
    uz_term: Mapped[str] = mapped_column(String(255), default="")
    en_term: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    example: Mapped[str] = mapped_column(Text, default="")
    is_slang_or_brand: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TeamMember(Base):
    __tablename__ = "team_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(128), nullable=False)
    languages: Mapped[str] = mapped_column(String(128), default="KK, RU")
    email: Mapped[str] = mapped_column(String(128), default="")
    avatar_initials: Mapped[str] = mapped_column(String(8), default="QA")
    is_active_reviewer: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
