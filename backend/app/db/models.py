"""SQLAlchemy ORM Models — Student Attention & Fatigue Detection System.

Implements CON §7, SYS-12, APP-12:
- All 11 tables from contracts.md §7.
- No BLOB/image columns anywhere (enforced by design).
- Foreign keys with cascade rules.
- Enum columns use only frozen contracts.md values.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # store as naive UTC


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Users & roles
# ---------------------------------------------------------------------------

class User(Base):
    """System users (teachers and admins). CON §7."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)          # "teacher" | "admin"
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    teacher = relationship("Teacher", back_populates="user", uselist=False)

    __table_args__ = (
        CheckConstraint("role IN ('teacher','admin')", name="ck_users_role"),
    )


class Teacher(Base):
    """Extended profile for teacher-role users. CON §7."""
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    display_name = Column(String(200), nullable=False)

    user = relationship("User", back_populates="teacher")
    classroom_links = relationship("TeacherClassroom", back_populates="teacher", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Students, classrooms, cameras
# ---------------------------------------------------------------------------

class Student(Base):
    """Student registry. CON §7. No image data stored."""
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_code = Column(String(50), nullable=False, unique=True)
    name = Column(String(200), nullable=False)
    department = Column(String(100), nullable=True)
    year = Column(Integer, nullable=True)
    class_name = Column(String(100), nullable=True)
    active = Column(Boolean, nullable=False, default=True)

    classroom_links = relationship("ClassroomStudent", back_populates="student", cascade="all, delete-orphan")


class Camera(Base):
    """Camera registry. CON §7."""
    __tablename__ = "cameras"

    id = Column(String(50), primary_key=True)          # e.g. "CAM-001"
    source_uri = Column(String(500), nullable=True)    # RTSP / USB / file path
    state = Column(String(20), nullable=False, default="Offline")  # Online|Offline|Degraded
    last_seen = Column(DateTime, nullable=True)

    classrooms = relationship("Classroom", back_populates="camera")

    __table_args__ = (
        CheckConstraint("state IN ('Online','Offline','Degraded')", name="ck_cameras_state"),
    )


class Classroom(Base):
    """Classroom configuration. CON §7."""
    __tablename__ = "classrooms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_name = Column(String(200), nullable=False)
    class_name = Column(String(100), nullable=False)
    camera_id = Column(String(50), ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
    active = Column(Boolean, nullable=False, default=True)

    camera = relationship("Camera", back_populates="classrooms")
    teacher_links = relationship("TeacherClassroom", back_populates="classroom", cascade="all, delete-orphan")
    student_links = relationship("ClassroomStudent", back_populates="classroom", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="classroom")


# ---------------------------------------------------------------------------
# Association tables
# ---------------------------------------------------------------------------

class TeacherClassroom(Base):
    """Many-to-many: teachers ↔ classrooms. CON §7."""
    __tablename__ = "teacher_classrooms"

    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), primary_key=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id", ondelete="CASCADE"), primary_key=True)

    teacher = relationship("Teacher", back_populates="classroom_links")
    classroom = relationship("Classroom", back_populates="teacher_links")


class ClassroomStudent(Base):
    """Many-to-many: classrooms ↔ students. CON §7."""
    __tablename__ = "classroom_students"

    classroom_id = Column(Integer, ForeignKey("classrooms.id", ondelete="CASCADE"), primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), primary_key=True)

    classroom = relationship("Classroom", back_populates="student_links")
    student = relationship("Student", back_populates="classroom_links")


# ---------------------------------------------------------------------------
# Sessions, observations, alerts
# ---------------------------------------------------------------------------

class Session(Base):
    """Monitoring session. CON §7, SYS-12."""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id", ondelete="RESTRICT"), nullable=False)
    started_at = Column(DateTime, nullable=False, default=_utcnow)
    ended_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="Scheduled")
    students_detected_max = Column(Integer, nullable=False, default=0)

    classroom = relationship("Classroom", back_populates="sessions")
    observations = relationship("Observation", back_populates="session", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="session", cascade="all, delete-orphan")
    track_roster = relationship("TrackRosterMap", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('Scheduled','Monitoring','Completed','Aborted')",
            name="ck_sessions_status",
        ),
        Index("ix_sessions_classroom_id", "classroom_id"),
        Index("ix_sessions_started_at", "started_at"),
    )


class TrackRosterMap(Base):
    """Anonymous track-id → student mapping (nullable per OQ-1). CON §7."""
    __tablename__ = "track_roster_map"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    track_id = Column(Integer, nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True)

    session = relationship("Session", back_populates="track_roster")
    student = relationship("Student")

    __table_args__ = (
        UniqueConstraint("session_id", "track_id", name="uq_track_roster_session_track"),
        Index("ix_track_roster_session_id", "session_id"),
    )


class Observation(Base):
    """Stored aggregate: one row per (session, track) per OBSERVATION_INTERVAL_S. CON §2.2, §7."""
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    track_id = Column(Integer, nullable=False)
    ts = Column(DateTime, nullable=False)                        # UTC timestamp of interval end

    # Status snapshot
    attention_status = Column(String(20), nullable=False, default="Unknown")
    fatigue_status = Column(String(20), nullable=False, default="Unknown")

    # Score aggregates
    attention_score_mean = Column(Float, nullable=False, default=0.0)
    fatigue_index_mean = Column(Float, nullable=False, default=0.0)
    confidence_mean = Column(Float, nullable=False, default=0.0)

    # Frame counts
    drowsy_frames = Column(Integer, nullable=False, default=0)
    total_frames = Column(Integer, nullable=False, default=0)

    session = relationship("Session", back_populates="observations")

    __table_args__ = (
        CheckConstraint(
            "attention_status IN ('Attentive','Distracted','Unknown')",
            name="ck_obs_attention_status",
        ),
        CheckConstraint(
            "fatigue_status IN ('Normal','Fatigued','Unknown')",
            name="ck_obs_fatigue_status",
        ),
        Index("ix_observations_session_track", "session_id", "track_id"),
        Index("ix_observations_ts", "ts"),
    )


class Alert(Base):
    """Alert record conforming to CON §2.3, §7. Status lifecycle: New→Viewed→Resolved."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=True)
    track_id = Column(Integer, nullable=True, default=0)
    label = Column(String(20), nullable=True, default="SYSTEM")                   # "S001", "SYSTEM", etc.
    type = Column(String(30), nullable=False)                    # "fatigue"|"distraction"|...
    status = Column(String(20), nullable=False, default="New")   # "New"|"Viewed"|"Resolved"
    message = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    viewed_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    session = relationship("Session", back_populates="alerts")

    __table_args__ = (
        CheckConstraint(
            "type IN ('fatigue','distraction','camera_offline','ai_offline')",
            name="ck_alerts_type",
        ),
        CheckConstraint(
            "status IN ('New','Viewed','Resolved')",
            name="ck_alerts_status",
        ),
        Index("ix_alerts_session_id", "session_id"),
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_created_at", "created_at"),
    )


