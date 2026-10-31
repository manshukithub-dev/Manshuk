from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.config import MAX_UPLOAD_BYTES
from backend.app.database import get_db
from backend.app.models import GlossaryTerm
from backend.app.schemas import GlossaryTermIn, GlossaryTermOut
from backend.app.services.glossary_service import export_glossary_csv, parse_glossary_csv

router = APIRouter(prefix="/api/glossary", tags=["glossary"])


@router.get("", response_model=list[GlossaryTermOut])
def list_glossary(
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(GlossaryTerm)
    if search and search.strip():
        q = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                GlossaryTerm.ru_term.ilike(q),
                GlossaryTerm.kk_term.ilike(q),
                GlossaryTerm.uz_term.ilike(q),
                GlossaryTerm.en_term.ilike(q),
                GlossaryTerm.description.ilike(q),
            )
        )
    terms = db.scalars(stmt.order_by(GlossaryTerm.id.asc())).all()
    return list(terms)


@router.post("", response_model=GlossaryTermOut)
def create_glossary_term(
    payload: GlossaryTermIn,
    db: Session = Depends(get_db),
):
    term = GlossaryTerm(
        ru_term=payload.ru_term.strip(),
        kk_term=payload.kk_term.strip(),
        uz_term=payload.uz_term.strip(),
        en_term=payload.en_term.strip(),
        description=payload.description.strip(),
        example=payload.example.strip(),
        is_slang_or_brand=payload.is_slang_or_brand,
    )
    db.add(term)
    db.commit()
    db.refresh(term)
    return term


@router.put("/{term_id}", response_model=GlossaryTermOut)
def update_glossary_term(
    term_id: int,
    payload: GlossaryTermIn,
    db: Session = Depends(get_db),
):
    term = db.get(GlossaryTerm, term_id)
    if not term:
        raise HTTPException(status_code=404, detail="Глоссарий термині табылмады.")
    term.ru_term = payload.ru_term.strip()
    term.kk_term = payload.kk_term.strip()
    term.uz_term = payload.uz_term.strip()
    term.en_term = payload.en_term.strip()
    term.description = payload.description.strip()
    term.example = payload.example.strip()
    term.is_slang_or_brand = payload.is_slang_or_brand
    db.commit()
    db.refresh(term)
    return term


@router.delete("/{term_id}")
def delete_glossary_term(
    term_id: int,
    db: Session = Depends(get_db),
):
    term = db.get(GlossaryTerm, term_id)
    if not term:
        raise HTTPException(status_code=404, detail="Глоссарий термині табылмады.")
    db.delete(term)
    db.commit()
    return {"ok": True}


@router.post("/import-csv")
async def import_glossary_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    raw_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="CSV файлы тым үлкен.")
    try:
        csv_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV файлы UTF-8 кодтауында болуы керек.") from exc

    parsed = parse_glossary_csv(csv_text)
    if not parsed:
        raise HTTPException(status_code=400, detail="CSV файлында жарамды терминдер табылмады.")

    existing_map = {
        t.ru_term.strip().lower(): t for t in db.scalars(select(GlossaryTerm)).all()
    }
    added = 0
    updated = 0
    for item in parsed:
        key_low = item["ru_term"].strip().lower()
        if key_low in existing_map:
            t = existing_map[key_low]
            t.kk_term = item["kk_term"]
            t.uz_term = item.get("uz_term", "")
            t.en_term = item.get("en_term", "")
            t.description = item.get("description", "")
            t.example = item.get("example", "")
            t.is_slang_or_brand = item.get("is_slang_or_brand", False)
            updated += 1
        else:
            db.add(GlossaryTerm(**item))
            added += 1
    db.commit()
    return {"added": added, "updated": updated, "total_imported": len(parsed)}


@router.get("/export-csv")
def export_glossary_as_csv(db: Session = Depends(get_db)):
    terms = list(db.scalars(select(GlossaryTerm).order_by(GlossaryTerm.id.asc())).all())
    csv_str = export_glossary_csv(terms)
    return Response(
        content="\ufeff" + csv_str,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="qazaq_locqa_glossary.csv"'},
    )
