"""Seed demo data for Student Attention & Fatigue Platform.

Creates default admin and teacher accounts, classrooms, and sample historical sessions.
Usage:
    python backend/scripts/seed_demo_data.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.database import create_tables, get_db_session
from app.db.models import (
    User,
    Teacher,
    Student,
    Classroom,
    Camera,
    TeacherClassroom,
    ClassroomStudent,
    Session,
    Observation,
    Alert,
)
from app.auth.jwt import hash_password


def seed():
    create_tables()
    with get_db_session() as db:
        print("[*] Seeding initial demo data...")

        # 1. Cameras
        cam1 = db.query(Camera).filter_by(id="CAM-001").first()
        if not cam1:
            cam1 = Camera(id="CAM-001", source_uri="0", state="Online")
            db.add(cam1)

        cam2 = db.query(Camera).filter_by(id="CAM-002").first()
        if not cam2:
            cam2 = Camera(id="CAM-002", source_uri="rtsp://192.168.1.100:554/live", state="Online")
            db.add(cam2)
        db.flush()

        # 2. Classrooms
        room1 = db.query(Classroom).filter_by(room_name="Lab 101").first()
        if not room1:
            room1 = Classroom(room_name="Lab 101", class_name="III AI & Data Science", camera_id="CAM-001", active=True)
            db.add(room1)

        room2 = db.query(Classroom).filter_by(room_name="Hall 204").first()
        if not room2:
            room2 = Classroom(room_name="Hall 204", class_name="IV Computer Science", camera_id="CAM-002", active=True)
            db.add(room2)
        db.flush()

        # 3. Users: Admin
        admin_user = db.query(User).filter_by(username="admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                password_hash=hash_password("adminpass"),
                role="admin",
                active=True,
            )
            db.add(admin_user)
            print("  [+] Created Admin: username='admin', password='<placeholder_adminpass>'")
        else:
            admin_user.password_hash = hash_password("adminpass")
            admin_user.active = True
            print("  [*] Updated Admin: username='admin', password='<placeholder_adminpass>'")

        # 4. Users: Teacher & Teacher1
        for uname, dname in [("teacher", "Prof. Teacher Demo"), ("teacher1", "Prof. Sarah Jenkins")]:
            t_user = db.query(User).filter_by(username=uname).first()
            if not t_user:
                t_user = User(
                    username=uname,
                    password_hash=hash_password("teachpass"),
                    role="teacher",
                    active=True,
                )
                db.add(t_user)
                db.flush()
                print(f"  [+] Created Teacher: username='{uname}', password='<placeholder_teachpass>' ({dname})")
            else:
                t_user.password_hash = hash_password("teachpass")
                t_user.active = True
                print(f"  [*] Updated Teacher: username='{uname}', password='<placeholder_teachpass>' ({dname})")

            t_profile = db.query(Teacher).filter_by(user_id=t_user.id).first()
            if not t_profile:
                t_profile = Teacher(user_id=t_user.id, display_name=dname)
                db.add(t_profile)
                db.flush()

            # Assign teacher to Lab 101
            link = db.query(TeacherClassroom).filter_by(teacher_id=t_profile.id, classroom_id=room1.id).first()
            if not link:
                db.add(TeacherClassroom(teacher_id=t_profile.id, classroom_id=room1.id))

        # 5. Sample Students
        students_data = [
            ("STU-001", "Alex Rivera", "III AI & Data Science"),
            ("STU-002", "Elena Rostova", "III AI & Data Science"),
            ("STU-003", "Marcus Chen", "III AI & Data Science"),
            ("STU-004", "Priya Patel", "III AI & Data Science"),
            ("STU-005", "David Kim", "III AI & Data Science"),
        ]
        for code, name, c_name in students_data:
            stu = db.query(Student).filter_by(student_code=code).first()
            if not stu:
                stu = Student(student_code=code, name=name, department="Computer Science", year=3, class_name=c_name, active=True)
                db.add(stu)
                db.flush()
                db.add(ClassroomStudent(classroom_id=room1.id, student_id=stu.id))

        # 6. Sample Completed Session for Reports
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        past_session = db.query(Session).filter_by(classroom_id=room1.id, status="Completed").first()
        if not past_session:
            past_session = Session(
                classroom_id=room1.id,
                started_at=now - timedelta(hours=2),
                ended_at=now - timedelta(hours=1),
                status="Completed",
                students_detected_max=25,
            )
            db.add(past_session)
            db.flush()

            # Add observations for historical charts
            for track_id in range(1, 26):
                db.add(Observation(
                    session_id=past_session.id,
                    track_id=track_id,
                    ts=now - timedelta(hours=1, minutes=30),
                    attention_status="Attentive" if track_id > 5 else "Distracted",
                    fatigue_status="Fatigued" if track_id <= 2 else "Normal",
                    attention_score_mean=84.5 if track_id > 5 else 48.0,
                    fatigue_index_mean=0.68 if track_id <= 2 else 0.18,
                    confidence_mean=0.94,
                    drowsy_frames=12 if track_id <= 2 else 0,
                    total_frames=60,
                ))

            # Add sample alert
            db.add(Alert(
                session_id=past_session.id,
                track_id=1,
                label="S001",
                type="fatigue",
                status="Resolved",
                message="Repeated fatigue-related indicators during the current session.",
                confidence=0.92,
                created_at=now - timedelta(hours=1, minutes=35),
                viewed_at=now - timedelta(hours=1, minutes=33),
                resolved_at=now - timedelta(hours=1, minutes=30),
            ))
            print(f"  [+] Seeded sample completed session #{past_session.id} for analytics reports.")

        # 7. Active Monitoring Session
        active_session = db.query(Session).filter_by(classroom_id=room1.id, status="Monitoring").first()
        if not active_session:
            active_session = Session(
                classroom_id=room1.id,
                started_at=now - timedelta(minutes=15),
                status="Monitoring",
                students_detected_max=18,
            )
            db.add(active_session)
            db.flush()

            # Add sample active alert
            db.add(Alert(
                session_id=active_session.id,
                track_id=3,
                label="S003",
                type="fatigue",
                status="New",
                message="Repeated fatigue-related indicators during the current session.",
                confidence=0.91,
                created_at=now - timedelta(minutes=4),
            ))
            db.add(Alert(
                session_id=active_session.id,
                track_id=7,
                label="S007",
                type="distraction",
                status="Viewed",
                message="Frequent off-task head pose detected over observation window.",
                confidence=0.88,
                created_at=now - timedelta(minutes=2),
                viewed_at=now - timedelta(minutes=1),
            ))
            print(f"  [+] Seeded active monitoring session #{active_session.id} for live dashboard.")

        print("[SUCCESS] Demo data seeding completed successfully!")


if __name__ == "__main__":
    seed()
