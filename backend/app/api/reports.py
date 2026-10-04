"""Reports API router — CON §3, CON §8, SYS-13, APP-13/14.

Endpoints:
- GET /reports: Historical session summaries.
- GET /reports/{session_id}: Full session report JSON.
- GET /reports/{session_id}/export?format=csv|pdf: Export session report file download.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.auth.jwt import require_teacher_or_admin
from app.db.database import get_db
from app.db.models import Classroom, Session, Teacher, TeacherClassroom, User
from app.reports.builder import build_session_report, export_csv, export_pdf

router = APIRouter(tags=["reports"])


def _teacher_can_access_session(db: DBSession, user: User, session: Session) -> bool:
    """Enforce that teachers only access sessions in assigned classrooms."""
    if user.role == "admin":
        return True

    teacher = db.query(Teacher).filter_by(user_id=user.id).first()
    if not teacher:
        return False

    link = (
        db.query(TeacherClassroom)
        .filter_by(teacher_id=teacher.id, classroom_id=session.classroom_id)
        .first()
    )
    return link is not None


@router.get("/reports", response_model=List[Dict[str, Any]], summary="List Reports")
def list_reports(
    limit: Optional[int] = Query(None, description="Max reports to return (clamped to 100)"),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_teacher_or_admin),
    db: DBSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List historical session summaries with role-based scoping and clamped pagination (DOS5)."""
    query = db.query(Session).filter(Session.status.in_(["Completed", "Monitoring"]))

    if current_user.role == "teacher":
        teacher = db.query(Teacher).filter_by(user_id=current_user.id).first()
        if not teacher:
            return []
        assigned_classroom_ids = [
            link.classroom_id
            for link in db.query(TeacherClassroom).filter_by(teacher_id=teacher.id).all()
        ]
        query = query.filter(Session.classroom_id.in_(assigned_classroom_ids))

    query = query.order_by(Session.started_at.desc())
    if limit is not None:
        effective_limit = min(max(1, limit), 100)
        query = query.offset(offset).limit(effective_limit)

    sessions = query.all()

    summaries = []
    for s in sessions:
        class_name = s.classroom.class_name if s.classroom else "Classroom"
        summaries.append({
            "session_id": s.id,
            "classroom_id": s.classroom_id,
            "class_name": class_name,
            "started_at": s.started_at.isoformat(),
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "status": s.status,
            "students_detected_max": s.students_detected_max,
        })
    return summaries


@router.get("/reports/{session_id}", response_model=Dict[str, Any], summary="Get Session Report JSON")
def get_session_report(
    session_id: int,
    current_user: User = Depends(require_teacher_or_admin),
    db: DBSession = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve full canonical JSON session report (CON §8)."""
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Session {session_id} not found."},
        )

    if not _teacher_can_access_session(db, current_user, session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "You cannot access reports for this session."},
        )

    try:
        return build_session_report(db, session_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "REPORT_ERROR", "message": str(exc)},
        )


@router.get("/reports/{session_id}/export", summary="Export Session Report")
def export_session_report(
    session_id: int,
    format: str = Query("csv", pattern="^(csv|pdf)$", description="Export format: csv or pdf"),
    current_user: User = Depends(require_teacher_or_admin),
    db: DBSession = Depends(get_db),
):
    """Download session report as CSV or PDF with exact aggregate matching and legal footer."""
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Session {session_id} not found."},
        )

    if not _teacher_can_access_session(db, current_user, session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "You cannot access reports for this session."},
        )

    report_data = build_session_report(db, session_id)

    if format.lower() == "csv":
        content = export_csv(report_data)
        return Response(
            content=content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="session_{session_id}_report.csv"'
            },
        )
    elif format.lower() == "pdf":
        pdf_bytes = export_pdf(report_data)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="session_{session_id}_report.pdf"'
            },
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_FORMAT", "message": "Supported formats are 'csv' and 'pdf'."},
        )
