"""Students router — CON §3, APP-7. Admin-only CRUD; deactivate instead of delete."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.auth.jwt import require_admin, require_teacher_or_admin
from app.db.database import get_db
from app.db.models import Classroom, ClassroomStudent, Student, TrackRosterMap, User

router = APIRouter(tags=["students"])


class StudentOut(BaseModel):
    id: int
    student_code: str
    name: str
    department: Optional[str] = None
    year: Optional[int] = None
    class_name: Optional[str] = None
    active: bool

    model_config = {"from_attributes": True}


class StudentCreate(BaseModel):
    student_code: str
    name: str
    department: Optional[str] = None
    year: Optional[int] = None
    class_name: Optional[str] = None


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    year: Optional[int] = None
    class_name: Optional[str] = None
    active: Optional[bool] = None


def _get_student_or_404(db: DBSession, student_id: int) -> Student:
    s = db.get(Student, student_id)
    if not s:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Student not found."})
    return s


@router.get("/students", response_model=List[StudentOut])
def list_students(
    current_user: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
) -> List[StudentOut]:
    return db.query(Student).filter_by(active=True).all()


@router.post("/students", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(
    body: StudentCreate,
    current_user: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
) -> StudentOut:
    student = Student(**body.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.get("/students/{student_id}", response_model=StudentOut)
def get_student(
    student_id: int,
    current_user: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
) -> StudentOut:
    return _get_student_or_404(db, student_id)



@router.put("/students/{student_id}", response_model=StudentOut)
def update_student(
    student_id: int,
    body: StudentUpdate,
    current_user: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
) -> StudentOut:
    student = _get_student_or_404(db, student_id)
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(student, field, val)
    db.commit()
    db.refresh(student)
    return student


@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_student(
    student_id: int,
    current_user: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
) -> None:
    """Deactivate rather than delete (APP-7)."""
    student = _get_student_or_404(db, student_id)
    student.active = False
    db.commit()


@router.post("/students/{student_id}/assign", status_code=status.HTTP_204_NO_CONTENT)
def assign_student_to_classroom(
    student_id: int,
    classroom_id: int,
    current_user: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
) -> None:
    """Assign a student to a classroom (admin only)."""
    _get_student_or_404(db, student_id)
    if not db.get(Classroom, classroom_id):
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Classroom not found."})
    existing = db.query(ClassroomStudent).filter_by(
        classroom_id=classroom_id, student_id=student_id
    ).first()
    if not existing:
        db.add(ClassroomStudent(classroom_id=classroom_id, student_id=student_id))
        db.commit()


@router.get("/students/roster-map/{session_id}", summary="Get Track to Student Roster Map (DB8)")
def get_track_roster_map(
    session_id: int,
    current_user: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
):
    """Retrieve track-to-student mapping. Strictly admin-only (DB8, OQ-1)."""
    records = db.query(TrackRosterMap).filter_by(session_id=session_id).all()
    return [
        {
            "id": r.id,
            "session_id": r.session_id,
            "track_id": r.track_id,
            "student_id": r.student_id,
        }
        for r in records
    ]

