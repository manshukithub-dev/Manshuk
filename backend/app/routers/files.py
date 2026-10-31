from __future__ import annotations

from pathlib import Path
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.config import (
    ALLOWED_ARB_EXTENSIONS,
    ALLOWED_CSV_EXTENSIONS,
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_MB,
    UPLOADS_DIR,
)
from backend.app.database import get_db
from backend.app.models import UploadedFile
from backend.app.routers.deps import get_workspace_token
from backend.app.schemas import UploadedFileOut
from backend.app.services.arb_parser import ARBValidationError, parse_arb_content
from backend.app.services.glossary_service import parse_glossary_csv

router = APIRouter(prefix="/api/files", tags=["files"])

VALID_ROLES = {"ru", "kk", "uz", "en", "glossary"}


@router.post("/upload", response_model=UploadedFileOut)
async def upload_localization_file(
    role: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    workspace_token: str = Depends(get_workspace_token),
):
    role_clean = role.strip().lower()
    if role_clean not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Белгісіз файл рөлі: {role}. Рұқсат етілгендері: ru, kk, uz, en, glossary.")

    filename = Path(file.filename or "uploaded_file").name
    ext = Path(filename).suffix.lower()

    if role_clean == "glossary":
        if ext not in ALLOWED_CSV_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Глоссарий файлы тек CSV форматында (.csv) болуы керек (берілгені: {ext or 'белгісіз'}).",
            )
    else:
        if ext not in ALLOWED_ARB_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Локализация файлы ARB немесе JSON форматында (.arb, .json) болуы керек (берілгені: {ext or 'белгісіз'}).",
            )

    raw_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Файл көлемі рұқсат етілген шектен ({MAX_UPLOAD_MB} МБ) асып кетті.",
        )
    if len(raw_bytes) == 0:
        raise HTTPException(status_code=400, detail=f"«{filename}» файлы бос.")

    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"«{filename}» файлы UTF-8 кодтауында болуы керек.",
        ) from exc

    if role_clean == "glossary":
        terms = parse_glossary_csv(raw_text)
        if not terms:
            raise HTTPException(
                status_code=400,
                detail=f"«{filename}» глоссарий файлынан жарамды терминдер табылмады. Баған атауларын (ru_term, kk_term, ...) тексеріңіз.",
            )
        line_count = raw_text.count("\n") + 1
        key_count = len(terms)
        file_format = "CSV"
    else:
        try:
            parsed = parse_arb_content(raw_text, filename=filename)
        except ARBValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        line_count = parsed.line_count
        key_count = len(parsed.entries)
        file_format = "ARB"

    ws_dir = UPLOADS_DIR / workspace_token
    safe_name = f"{uuid.uuid4().hex[:12]}_{filename}"
    stored_path = ws_dir / safe_name
    try:
        ws_dir.mkdir(parents=True, exist_ok=True)
        stored_path.write_text(raw_text, encoding="utf-8")
    except OSError:
        # In cloud deployments with ephemeral/read-only disks, raw_content in PostgreSQL is authoritative
        pass

    db_file = UploadedFile(
        workspace_token=workspace_token,
        role=role_clean,
        original_filename=filename,
        stored_path=str(stored_path),
        file_format=file_format,
        size_bytes=len(raw_bytes),
        line_count=line_count,
        key_count=key_count,
        is_valid=True,
        validation_error=None,
        is_demo=False,
        raw_content=raw_text,
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file


@router.get("", response_model=list[UploadedFileOut])
def list_files(
    db: Session = Depends(get_db),
    workspace_token: str = Depends(get_workspace_token),
):
    rows = db.scalars(
        select(UploadedFile)
        .where(UploadedFile.workspace_token == workspace_token)
        .order_by(UploadedFile.created_at.desc())
        .limit(100)
    ).all()
    return list(rows)


@router.get("/{file_id}/preview")
def preview_file(
    file_id: int,
    db: Session = Depends(get_db),
    workspace_token: str = Depends(get_workspace_token),
):
    f = db.scalar(
        select(UploadedFile).where(
            UploadedFile.id == file_id,
            UploadedFile.workspace_token == workspace_token,
        )
    )
    if not f:
        raise HTTPException(status_code=404, detail="Файл табылмады.")

    raw = f.raw_content or ""
    if f.file_format == "ARB":
        parsed = parse_arb_content(raw, f.original_filename)
        sample_items = [
            {
                "key": k,
                "value": v,
                "has_metadata": k in parsed.metadata,
            }
            for k, v in list(parsed.entries.items())[:30]
        ]
        return {
            "id": f.id,
            "filename": f.original_filename,
            "role": f.role,
            "format": f.file_format,
            "locale": parsed.locale,
            "key_count": len(parsed.entries),
            "metadata_count": len(parsed.metadata),
            "line_count": f.line_count,
            "size_bytes": f.size_bytes,
            "sample": sample_items,
        }
    else:
        terms = parse_glossary_csv(raw)
        return {
            "id": f.id,
            "filename": f.original_filename,
            "role": f.role,
            "format": f.file_format,
            "locale": "multi",
            "key_count": len(terms),
            "metadata_count": 0,
            "line_count": f.line_count,
            "size_bytes": f.size_bytes,
            "sample": terms[:30],
        }


@router.get("/{file_id}/download")
def download_file_raw(
    file_id: int,
    db: Session = Depends(get_db),
    workspace_token: str = Depends(get_workspace_token),
):
    f = db.scalar(
        select(UploadedFile).where(
            UploadedFile.id == file_id,
            UploadedFile.workspace_token == workspace_token,
        )
    )
    if not f or f.raw_content is None:
        raise HTTPException(status_code=404, detail="Файл табылмады.")
    media = "text/csv; charset=utf-8" if f.file_format == "CSV" else "application/json; charset=utf-8"
    clean_name = f.original_filename.replace("[DEMO] ", "")
    return Response(
        content=f.raw_content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{clean_name}"'},
    )


@router.delete("/{file_id}")
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    workspace_token: str = Depends(get_workspace_token),
):
    f = db.scalar(
        select(UploadedFile).where(
            UploadedFile.id == file_id,
            UploadedFile.workspace_token == workspace_token,
        )
    )
    if not f:
        raise HTTPException(status_code=404, detail="Файл табылмады.")
    try:
        p = Path(f.stored_path)
        if p.exists() and not f.is_demo:
            p.unlink(missing_ok=True)
        if p.parent.exists() and p.parent != UPLOADS_DIR and not any(p.parent.iterdir()):
            p.parent.rmdir()
    except OSError:
        pass
    db.delete(f)
    db.commit()
    return {"ok": True}
