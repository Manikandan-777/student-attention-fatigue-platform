"""Teachers router — CON §3, APP-9. Admin-only management of teacher accounts."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.auth.jwt import hash_password, require_admin, validate_password_strength
from app.config import settings
from app.db.database import get_db
from app.db.models import Classroom, Teacher, TeacherClassroom, User

router = APIRouter(tags=["teachers"])


class TeacherOut(BaseModel):
    id: int
    user_id: int
    display_name: str
    username: str
    active: bool
    classroom_name: Optional[str] = None
    classroom_id: Optional[int] = None

    model_config = {"from_attributes": True}


class TeacherCreate(BaseModel):
    username: str
    password: str
    display_name: str
    classroom_id: Optional[int] = None
    active: Optional[bool] = True


class TeacherUpdate(BaseModel):
    display_name: Optional[str] = None
    active: Optional[bool] = None
    classroom_id: Optional[int] = None


def _get_teacher_or_404(db: DBSession, teacher_id: int) -> Teacher:
    t = db.get(Teacher, teacher_id)
    if not t:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Teacher not found."})
    return t


def _teacher_to_out(t: Teacher) -> TeacherOut:
    c_name = None
    c_id = None
    if t.classroom_links and len(t.classroom_links) > 0 and t.classroom_links[0].classroom:
        c_name = t.classroom_links[0].classroom.class_name
        c_id = t.classroom_links[0].classroom_id
    return TeacherOut(
        id=t.id,
        user_id=t.user_id,
        display_name=t.display_name,
        username=t.user.username,
        active=t.user.active,
        classroom_name=c_name,
        classroom_id=c_id,
    )


@router.get("/teachers", response_model=List[TeacherOut])
def list_teachers(
    current_user: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
) -> List[TeacherOut]:
    teachers = db.query(Teacher).all()
    return [_teacher_to_out(t) for t in teachers]


@router.post("/teachers", response_model=TeacherOut, status_code=status.HTTP_201_CREATED)
def create_teacher(
    body: TeacherCreate,
    current_user: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
) -> TeacherOut:
    """Create a new teacher user account (admin only)."""
    if settings.PASSWORD_POLICY_STRICT:
        validate_password_strength(body.password)
    if db.query(User).filter_by(username=body.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": f"Username '{body.username}' already exists."},
        )
    is_active = True if body.active is None else body.active
    user = User(username=body.username, password_hash=hash_password(body.password), role="teacher", active=is_active)
    db.add(user)
    db.flush()
    teacher = Teacher(user_id=user.id, display_name=body.display_name)
    db.add(teacher)
    db.flush()
    if body.classroom_id:
        cls = db.get(Classroom, body.classroom_id)
        if cls:
            db.add(TeacherClassroom(teacher_id=teacher.id, classroom_id=body.classroom_id))
    db.commit()
    db.refresh(teacher)
    return _teacher_to_out(teacher)


@router.get("/teachers/{teacher_id}", response_model=TeacherOut)
def get_teacher(
    teacher_id: int,
    current_user: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
) -> TeacherOut:
    return _teacher_to_out(_get_teacher_or_404(db, teacher_id))


@router.put("/teachers/{teacher_id}", response_model=TeacherOut)
def update_teacher(
    teacher_id: int,
    body: TeacherUpdate,
    current_user: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
) -> TeacherOut:
    teacher = _get_teacher_or_404(db, teacher_id)
    if body.display_name is not None:
        teacher.display_name = body.display_name
    if body.active is not None:
        teacher.user.active = body.active
    if body.classroom_id is not None:
        db.query(TeacherClassroom).filter_by(teacher_id=teacher.id).delete()
        if body.classroom_id > 0 and db.get(Classroom, body.classroom_id):
            db.add(TeacherClassroom(teacher_id=teacher.id, classroom_id=body.classroom_id))
    db.commit()
    db.refresh(teacher)
    return _teacher_to_out(teacher)


@router.delete("/teachers/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_teacher(
    teacher_id: int,
    current_user: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
) -> None:
    """Deactivate teacher account (admin only). Admin cannot delete themselves."""
    teacher = _get_teacher_or_404(db, teacher_id)
    if teacher.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": "Admin cannot delete their own account."},
        )
    teacher.user.active = False
    db.commit()


@router.post("/teachers/{teacher_id}/assign-classroom", status_code=status.HTTP_204_NO_CONTENT)
def assign_classroom(
    teacher_id: int,
    classroom_id: int,
    current_user: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
) -> None:
    """Assign a teacher to a classroom (admin only)."""
    _get_teacher_or_404(db, teacher_id)
    if not db.get(Classroom, classroom_id):
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Classroom not found."})
    existing = db.query(TeacherClassroom).filter_by(
        teacher_id=teacher_id, classroom_id=classroom_id
    ).first()
    if not existing:
        db.add(TeacherClassroom(teacher_id=teacher_id, classroom_id=classroom_id))
        db.commit()
