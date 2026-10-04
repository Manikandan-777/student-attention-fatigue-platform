"""Classrooms & Cameras router — CON §3, APP-5/7/9.

Admin-only CRUD for classrooms and cameras.
Teachers can list classrooms they are assigned to.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.auth.jwt import get_current_user, require_admin, require_teacher_or_admin
from app.db.database import get_db
from app.db.models import Camera, Classroom, Teacher, TeacherClassroom, User

router = APIRouter(tags=["classrooms"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CameraOut(BaseModel):
    """Camera public response — id and state only, never credentials or source_uri (CAM1)."""
    id: str
    state: str

    model_config = {"from_attributes": True}


class CameraCreate(BaseModel):
    id: str
    source_uri: Optional[str] = None
    state: str = "Offline"


class ClassroomOut(BaseModel):
    id: int
    room_name: str
    class_name: str
    camera_id: Optional[str] = None
    active: bool

    model_config = {"from_attributes": True}


class ClassroomCreate(BaseModel):
    room_name: str
    class_name: str
    camera_id: Optional[str] = None


class ClassroomUpdate(BaseModel):
    room_name: Optional[str] = None
    class_name: Optional[str] = None
    camera_id: Optional[str] = None
    active: Optional[bool] = None


# ---------------------------------------------------------------------------
# Helpers & Validators
# ---------------------------------------------------------------------------

ALLOWED_CAMERA_SCHEMES = ("rtsp://", "file://")
FORBIDDEN_CAMERA_PATTERNS = ("169.254.", "/etc/passwd", "windows/system32", "http://", "https://", "ftp://")


def validate_camera_source_uri(uri: Optional[str]) -> None:
    """Validate camera source URI scheme and SSRF safety (CAM3, CAM4)."""
    if not uri:
        return
    uri_clean = uri.strip().lower()
    # Digits are allowed for direct local device index (e.g., '0' for webcams)
    if uri_clean.isdigit():
        return
    if not any(uri_clean.startswith(s) for s in ALLOWED_CAMERA_SCHEMES):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_CAMERA_URI", "message": "Camera URI must use rtsp://, file://, or device index."},
        )
    for pattern in FORBIDDEN_CAMERA_PATTERNS:
        if pattern in uri_clean:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "SSRF_DETECTED", "message": "Camera URI target is forbidden."},
            )


def _get_classroom_or_404(db: DBSession, classroom_id: int) -> Classroom:
    room = db.get(Classroom, classroom_id)

    if not room:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Classroom not found."})
    return room


def _teacher_can_access(db: DBSession, user: User, classroom_id: int) -> bool:
    """Teachers may only access classrooms they are assigned to."""
    if user.role == "admin":
        return True
    teacher = db.query(Teacher).filter_by(user_id=user.id).first()
    if not teacher:
        return False
    link = db.query(TeacherClassroom).filter_by(
        teacher_id=teacher.id, classroom_id=classroom_id
    ).first()
    return link is not None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/classrooms", response_model=List[ClassroomOut])
def list_classrooms(
    current_user: User = Depends(require_teacher_or_admin),
    db: DBSession = Depends(get_db),
) -> List[ClassroomOut]:
    """List all classrooms (teachers see only their assigned ones)."""
    if current_user.role == "admin":
        rooms = db.query(Classroom).filter_by(active=True).all()
    else:
        teacher = db.query(Teacher).filter_by(user_id=current_user.id).first()
        if not teacher:
            return []
        rooms = (
            db.query(Classroom)
            .join(TeacherClassroom, TeacherClassroom.classroom_id == Classroom.id)
            .filter(TeacherClassroom.teacher_id == teacher.id, Classroom.active == True)
            .all()
        )
    return rooms


@router.post("/classrooms", response_model=ClassroomOut, status_code=status.HTTP_201_CREATED)
def create_classroom(
    body: ClassroomCreate,
    current_user: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
) -> ClassroomOut:
    """Create a new classroom (admin only)."""
    room = Classroom(**body.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.put("/classrooms/{classroom_id}", response_model=ClassroomOut)
def update_classroom(
    classroom_id: int,
    body: ClassroomUpdate,
    current_user: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
) -> ClassroomOut:
    """Update classroom details (admin only)."""
    room = _get_classroom_or_404(db, classroom_id)
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(room, field, val)
    db.commit()
    db.refresh(room)
    return room


@router.delete("/classrooms/{classroom_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_classroom(
    classroom_id: int,
    current_user: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
) -> None:
    """Soft-delete a classroom by setting active=False (admin only)."""
    room = _get_classroom_or_404(db, classroom_id)
    room.active = False
    db.commit()


@router.post("/cameras", response_model=CameraOut, status_code=status.HTTP_201_CREATED)
def create_camera(
    body: CameraCreate,
    current_user: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
) -> CameraOut:
    """Register camera with URI scheme validation and SSRF defenses (CAM3, CAM4)."""
    validate_camera_source_uri(body.source_uri)
    if db.get(Camera, body.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": f"Camera '{body.id}' already exists."},
        )
    cam = Camera(id=body.id, source_uri=body.source_uri, state=body.state)
    db.add(cam)
    db.commit()
    db.refresh(cam)
    return cam

