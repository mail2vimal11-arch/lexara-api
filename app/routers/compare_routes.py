"""Contract comparison routes — Excel and semantic clause comparison."""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.compare_service import compare_excel_contracts, compare_clause_texts
from app.models.user import User
from app.security import get_current_user
from app.services.audit_service import log_action

router = APIRouter(prefix="/compare", tags=["Compare"])


class ClauseCompareRequest(BaseModel):
    clause_a: str
    clause_b: str


@router.post("/excel")
async def compare_excel(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Compare two Excel contract files field by field.
    Returns mismatches and a match summary.
    """
    if not file_a.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="file_a must be an Excel file (.xlsx or .xls)")
    if not file_b.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="file_b must be an Excel file (.xlsx or .xls)")

    bytes_a = await file_a.read()
    bytes_b = await file_b.read()

    try:
        result = compare_excel_contracts(bytes_a, bytes_b)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    log_action(db, "CONTRACT_EXCEL_COMPARED",
               {"file_a": file_a.filename, "file_b": file_b.filename, "mismatches": len(result["mismatches"])},
               user_id=current_user.id)
    return result


@router.post("/clauses")
def compare_clauses(
    req: ClauseCompareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Semantically compare two clause texts.
    Returns cosine similarity score and match verdict.
    """
    result = compare_clause_texts(req.clause_a, req.clause_b)
    log_action(db, "CLAUSE_COMPARED",
               {"similarity": result["similarity_score"], "verdict": result["verdict"]},
               user_id=current_user.id)
    return result
