from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class UploadedFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int | None = None
    role: str
    original_filename: str
    file_format: str
    size_bytes: int
    line_count: int
    key_count: int
    is_valid: bool
    validation_error: str | None = None
    is_demo: bool = False
    created_at: datetime


class ProjectRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_demo: bool
    status: str
    source_locale: str
    has_kk: bool
    has_uz: bool
    has_en: bool
    total_keys: int
    checked_strings: int
    total_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    fixed_count: int
    human_reviewed_count: int
    kk_quality_score: float
    uz_quality_score: float | None = None
    ai_mode_used: str
    duration_ms: int
    created_at: datetime


class RunCreateRequest(BaseModel):
    name: str = Field(default="Локализация тексеруі", min_length=1, max_length=255)
    ru_file_id: int
    kk_file_id: int | None = None
    uz_file_id: int | None = None
    en_file_id: int | None = None
    glossary_file_id: int | None = None
    use_llm: bool = True


class IssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    entry_id: int
    lang: str
    key: str
    issue_type: str
    severity: str
    source: str
    target: str
    evidence: str
    suggestion: str
    confidence: float
    auto_fix_safe: bool
    reviewed_by_human: bool
    resolution: str
    resolved_by: str | None = None
    updated_at: datetime
    en_text: str | None = None
    current_target: str | None = None
    latin_preview: str | None = None
    entry_review_status: str | None = None


class IssueActionRequest(BaseModel):
    action: str = Field(
        ...,
        description="accept_suggestion | manual_edit | mark_reviewed | reject_suggestion | auto_apply",
    )
    new_target: str | None = None
    reviewer_name: str | None = None


class EntryUpdateRequest(BaseModel):
    current_target: str
    reviewed_by_human: bool = True
    reviewer_name: str | None = None


class GlossaryTermIn(BaseModel):
    ru_term: str = Field(..., min_length=1, max_length=255)
    kk_term: str = Field(..., min_length=1, max_length=255)
    uz_term: str = Field(default="", max_length=255)
    en_term: str = Field(default="", max_length=255)
    description: str = Field(default="")
    example: str = Field(default="")
    is_slang_or_brand: bool = False


class GlossaryTermOut(GlossaryTermIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class TeamMemberIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    role: str = Field(..., min_length=1, max_length=128)
    languages: str = Field(default="KK, RU")
    email: str = Field(default="")
    is_active_reviewer: bool = False


class TeamMemberOut(TeamMemberIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    avatar_initials: str
    reviewed_count: int = 0
    created_at: datetime


class SettingsUpdateRequest(BaseModel):
    llm_provider: str = Field(default="gemini")
    llm_api_key: str | None = None
    clear_api_key: bool = False
    llm_model: str = Field(default="gemini-2.5-flash")
    llm_base_url: str = Field(default="")
    length_overflow_ratio: float = Field(default=1.45, ge=1.1, le=3.0)
    button_max_chars: int = Field(default=24, ge=8, le=120)
    latin_check_enabled: bool = True


class SettingsOut(BaseModel):
    llm_provider: str
    has_api_key: bool
    masked_api_key: str
    llm_model: str
    llm_base_url: str
    length_overflow_ratio: float
    button_max_chars: int
    latin_check_enabled: bool
    max_upload_mb: int


class TransliterateRequest(BaseModel):
    text: str
    max_length: int | None = None


class TransliterateOut(BaseModel):
    source_cyrillic: str
    latin_text: str
    cyrillic_length: int
    latin_length: int
    length_delta: int
    overflow: bool


class DashboardStatsOut(BaseModel):
    has_runs: bool
    active_run: ProjectRunOut | None = None
    total_runs_count: int = 0
    total_checked_strings: int
    total_issues: int
    high_severity_issues: int
    medium_severity_issues: int = 0
    low_severity_issues: int = 0
    fixed_strings: int
    human_reviewed_strings: int
    unreviewed_strings: int
    kk_quality_score: float
    uz_quality_score: float | None
    issues_by_type: list[dict[str, Any]]
    severity_breakdown: list[dict[str, Any]]
    runs_trend: list[dict[str, Any]]
    language_comparison: list[dict[str, Any]]
    recent_runs: list[ProjectRunOut] = []
