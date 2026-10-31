from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.config import MAX_UPLOAD_MB
from backend.app.database import get_db
from backend.app.schemas import SettingsOut, SettingsUpdateRequest
from backend.app.services.llm_service import (
    get_setting,
    mask_secret,
    set_setting,
    test_llm_connection,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _build_settings_out(db: Session) -> SettingsOut:
    api_key = get_setting(db, "llm_api_key", "")
    return SettingsOut(
        llm_provider=get_setting(db, "llm_provider", "gemini"),
        has_api_key=bool(api_key),
        masked_api_key=mask_secret(api_key),
        llm_model=get_setting(db, "llm_model", "gemini-2.5-flash"),
        llm_base_url=get_setting(db, "llm_base_url", ""),
        length_overflow_ratio=float(get_setting(db, "length_overflow_ratio", "1.45")),
        button_max_chars=int(get_setting(db, "button_max_chars", "24")),
        latin_check_enabled=get_setting(db, "latin_check_enabled", "true").lower() == "true",
        max_upload_mb=MAX_UPLOAD_MB,
    )


@router.get("", response_model=SettingsOut)
def read_settings(db: Session = Depends(get_db)):
    return _build_settings_out(db)


@router.put("", response_model=SettingsOut)
def update_settings(payload: SettingsUpdateRequest, db: Session = Depends(get_db)):
    set_setting(db, "llm_provider", payload.llm_provider.strip().lower())
    set_setting(db, "llm_model", payload.llm_model.strip())
    set_setting(db, "llm_base_url", payload.llm_base_url.strip())
    set_setting(db, "length_overflow_ratio", str(payload.length_overflow_ratio))
    set_setting(db, "button_max_chars", str(payload.button_max_chars))
    set_setting(db, "latin_check_enabled", "true" if payload.latin_check_enabled else "false")

    # Never overwrite API key unless explicitly provided or cleared
    if payload.clear_api_key:
        set_setting(db, "llm_api_key", "")
    elif payload.llm_api_key is not None and payload.llm_api_key.strip() != "":
        set_setting(db, "llm_api_key", payload.llm_api_key.strip())

    db.commit()
    return _build_settings_out(db)


@router.post("/test-llm")
def check_llm_connectivity(db: Session = Depends(get_db)):
    provider = get_setting(db, "llm_provider", "gemini")
    api_key = get_setting(db, "llm_api_key", "")
    model = get_setting(db, "llm_model", "gemini-2.5-flash")
    base_url = get_setting(db, "llm_base_url", "")
    ok, message = test_llm_connection(provider=provider, api_key=api_key, model=model, base_url=base_url)
    return {"ok": ok, "message": message, "mode": "hybrid_llm" if ok else "rule_engine"}
