"""Phase 16 Test Suite — Export & Reporting Engine.

Spec refs: SYS-13, APP-13/14, CON §3, CON §8.
Pass conditions:
- build_session_report produces JSON strictly conforming to contracts.md §8.
- CSV export contains every aggregate count matching the JSON report exactly.
- PDF export contains every aggregate count matching the JSON report exactly.
- Both CSV and PDF contain the mandatory legal footer:
  "AI-generated indicators to support teacher observation; not a diagnosis or disciplinary record."
- REST API /reports lists historical summaries.
- REST API /reports/{id} returns report JSON with teacher classroom scoping.
- REST API /reports/{id}/export?format=csv|pdf returns downloadable file with correct headers.
- Teachers cannot access reports for unassigned classrooms (403).
- Unauthenticated requests return 401.
"""

from datetime import datetime, timedelta, timezone
import io
import pytest
import csv
from pypdf import PdfReader
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.jwt import create_access_token, hash_password
from app.db.database import get_db
from app.db.models import (
    Alert,
    Base,
    Camera,
    Classroom,
    Observation,
    Session,
    Teacher,
    TeacherClassroom,
    User,
)
from app.main import app
from app.reports.builder import (
    MANDATORY_FOOTER,
    build_session_report,
    export_csv,
    export_pdf,
)

# ---------------------------------------------------------------------------
# Test DB setup with isolated dependency overrides
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite:///./test_phase16.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    expire_on_commit=False,
)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_teardown_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Seed Helpers
# ---------------------------------------------------------------------------

def _seed_admin(db) -> User:
    u = User(username="admin_rep", password_hash=hash_password("adminpass"), role="admin")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _seed_teacher(db, username="teacher_rep", password="teachpass") -> tuple:
    u = User(username=username, password_hash=hash_password(password), role="teacher")
    db.add(u)
    db.flush()
    t = Teacher(user_id=u.id, display_name=f"Prof. {username.capitalize()}")
    db.add(t)
    db.commit()
    db.refresh(t)
    return u, t


def _seed_full_session(db) -> tuple:
    """Create a fully populated session with classroom, observations, and alerts."""
    cam = Camera(id="CAM-REP-1", state="Online")
    db.merge(cam)
    db.flush()

    room = Classroom(room_name="Lab 401", class_name="III AI & DS", camera_id="CAM-REP-1")
    db.add(room)
    db.flush()

    start_time = datetime(2026, 9, 30, 9, 0, 0)
    end_time = datetime(2026, 9, 30, 10, 0, 0)

    sess = Session(
        classroom_id=room.id,
        started_at=start_time,
        ended_at=end_time,
        status="Completed",
        students_detected_max=3,
    )
    db.add(sess)
    db.flush()

    # Track 1: S001 — Attentive, Normal
    db.add(Observation(
        session_id=sess.id,
        track_id=1,
        ts=start_time + timedelta(minutes=10),
        attention_status="Attentive",
        fatigue_status="Normal",
        attention_score_mean=88.0,
        fatigue_index_mean=0.15,
        confidence_mean=0.95,
        drowsy_frames=0,
        total_frames=120,
    ))
    db.add(Observation(
        session_id=sess.id,
        track_id=1,
        ts=start_time + timedelta(minutes=30),
        attention_status="Attentive",
        fatigue_status="Normal",
        attention_score_mean=92.0,
        fatigue_index_mean=0.10,
        confidence_mean=0.96,
        drowsy_frames=0,
        total_frames=120,
    ))

    # Track 2: S002 — Distracted, Normal
    db.add(Observation(
        session_id=sess.id,
        track_id=2,
        ts=start_time + timedelta(minutes=15),
        attention_status="Distracted",
        fatigue_status="Normal",
        attention_score_mean=45.0,
        fatigue_index_mean=0.20,
        confidence_mean=0.90,
        drowsy_frames=0,
        total_frames=120,
    ))
    db.add(Observation(
        session_id=sess.id,
        track_id=2,
        ts=start_time + timedelta(minutes=45),
        attention_status="Distracted",
        fatigue_status="Normal",
        attention_score_mean=40.0,
        fatigue_index_mean=0.25,
        confidence_mean=0.88,
        drowsy_frames=0,
        total_frames=120,
    ))

    # Track 3: S003 — Attentive, Fatigued
    db.add(Observation(
        session_id=sess.id,
        track_id=3,
        ts=start_time + timedelta(minutes=20),
        attention_status="Attentive",
        fatigue_status="Fatigued",
        attention_score_mean=70.0,
        fatigue_index_mean=0.65,
        confidence_mean=0.92,
        drowsy_frames=30,
        total_frames=120,
    ))

    # Alerts for session
    db.add(Alert(
        session_id=sess.id,
        track_id=2,
        label="S002",
        type="distraction",
        status="New",
        message="Repeated distraction-related indicators during the current session.",
        confidence=0.89,
        created_at=start_time + timedelta(minutes=16),
    ))
    db.add(Alert(
        session_id=sess.id,
        track_id=3,
        label="S003",
        type="fatigue",
        status="Viewed",
        message="Repeated fatigue-related indicators during the current session.",
        confidence=0.92,
        created_at=start_time + timedelta(minutes=22),
    ))

    db.commit()
    db.refresh(sess)
    return room, sess


def _auth(role="admin", username="admin_rep"):
    token = create_access_token(subject=username, role=role)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Unit Tests — Report Builder & Exporters
# ---------------------------------------------------------------------------

class TestReportBuilder:
    def test_build_session_report_conforms_to_contracts(self):
        db = TestSessionLocal()
        room, sess = _seed_full_session(db)

        report = build_session_report(db, sess.id)

        assert report["session_id"] == sess.id
        assert report["class_name"] == "III AI & DS"
        assert report["date"] == "2026-09-30"
        assert report["start"] == "09:00"
        assert report["end"] == "10:00"
        assert report["duration_min"] == 60
        assert report["students"] == 3

        # Attention: S001 (Attentive), S002 (Distracted), S003 (Attentive) → 2 attentive, 1 distracted, 0 unknown
        assert report["attention"]["attentive"] == 2
        assert report["attention"]["distracted"] == 1
        assert report["attention"]["unknown"] == 0

        # Fatigue: S001 (Normal), S002 (Normal), S003 (Fatigued) → 2 normal, 1 fatigued
        assert report["fatigue"]["normal"] == 2
        assert report["fatigue"]["fatigued"] == 1

        assert report["alerts_total"] == 2
        assert report["avg_attention_score"] > 0

        # Per student verification
        assert len(report["per_student"]) == 3
        s1 = next(s for s in report["per_student"] if s["label"] == "S001")
        assert s1["attention_mean"] == 90.0  # (88 + 92) / 2
        assert s1["fatigue_indicators"] == 0
        assert s1["alerts"] == 0

        s2 = next(s for s in report["per_student"] if s["label"] == "S002")
        assert s2["distraction_indicators"] == 2
        assert s2["alerts"] == 1

        s3 = next(s for s in report["per_student"] if s["label"] == "S003")
        assert s3["fatigue_indicators"] == 1
        assert s3["alerts"] == 1

        db.close()

    def test_export_csv_matches_json_counts_and_has_footer(self):
        db = TestSessionLocal()
        _, sess = _seed_full_session(db)
        report = build_session_report(db, sess.id)

        csv_text = export_csv(report)
        reader = list(csv.reader(io.StringIO(csv_text)))

        # Find mandatory footer
        flat_cells = [cell for row in reader for cell in row]
        assert MANDATORY_FOOTER in flat_cells, "Mandatory footer missing from CSV!"

        # Extract counts from CSV
        csv_dict = {row[0]: row[1] for row in reader if len(row) == 2}
        assert int(csv_dict["Total Students"]) == report["students"]
        assert int(csv_dict["Alerts Total"]) == report["alerts_total"]
        assert float(csv_dict["Average Attention Score"]) == report["avg_attention_score"]

        assert int(csv_dict["Attentive"]) == report["attention"]["attentive"]
        assert int(csv_dict["Distracted"]) == report["attention"]["distracted"]
        assert int(csv_dict["Unknown"]) == report["attention"]["unknown"]

        assert int(csv_dict["Normal"]) == report["fatigue"]["normal"]
        assert int(csv_dict["Fatigued"]) == report["fatigue"]["fatigued"]

        db.close()

    def test_export_pdf_matches_json_counts_and_has_footer(self):
        db = TestSessionLocal()
        _, sess = _seed_full_session(db)
        report = build_session_report(db, sess.id)

        pdf_bytes = export_pdf(report)
        assert len(pdf_bytes) > 500
        assert pdf_bytes.startswith(b"%PDF")

        # Extract text using pypdf
        reader = PdfReader(io.BytesIO(pdf_bytes))
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() + "\n"

        # Verify mandatory footer exists in PDF text
        assert "AI-generated indicators to support teacher observation" in full_text
        assert "not a diagnosis or disciplinary record" in full_text

        # Verify key aggregates are present in PDF text
        assert "III AI & DS" in full_text
        assert str(report["students"]) in full_text
        assert str(report["alerts_total"]) in full_text
        assert str(report["attention"]["attentive"]) in full_text
        assert str(report["fatigue"]["fatigued"]) in full_text
        assert "S001" in full_text
        assert "S002" in full_text
        assert "S003" in full_text

        db.close()


# ---------------------------------------------------------------------------
# API Tests — Reports Endpoints & Scoping
# ---------------------------------------------------------------------------

class TestReportsAPI:
    def test_unauthenticated_returns_401(self, client):
        assert client.get("/reports").status_code == 401
        assert client.get("/reports/1").status_code == 401
        assert client.get("/reports/1/export?format=csv").status_code == 401

    def test_admin_can_access_all_reports(self, client):
        db = TestSessionLocal()
        _seed_admin(db)
        _, sess = _seed_full_session(db)
        db.close()

        headers = _auth(role="admin", username="admin_rep")

        # 1. List
        res_list = client.get("/reports", headers=headers)
        assert res_list.status_code == 200
        assert len(res_list.json()) >= 1
        assert res_list.json()[0]["session_id"] == sess.id

        # 2. Detail JSON
        res_detail = client.get(f"/reports/{sess.id}", headers=headers)
        assert res_detail.status_code == 200
        data = res_detail.json()
        assert data["session_id"] == sess.id
        assert data["students"] == 3
        assert data["alerts_total"] == 2

        # 3. Export CSV
        res_csv = client.get(f"/reports/{sess.id}/export?format=csv", headers=headers)
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.headers["content-type"]
        assert f'filename="session_{sess.id}_report.csv"' in res_csv.headers["content-disposition"]
        assert MANDATORY_FOOTER in res_csv.text

        # 4. Export PDF
        res_pdf = client.get(f"/reports/{sess.id}/export?format=pdf", headers=headers)
        assert res_pdf.status_code == 200
        assert "application/pdf" in res_pdf.headers["content-type"]
        assert f'filename="session_{sess.id}_report.pdf"' in res_pdf.headers["content-disposition"]
        assert res_pdf.content.startswith(b"%PDF")

    def test_teacher_scoping_assigned_vs_unassigned(self, client):
        db = TestSessionLocal()
        u_t, teacher = _seed_teacher(db, "teacher_rep")
        room_assigned, sess_assigned = _seed_full_session(db)

        # Another unassigned classroom/session
        room_other = Classroom(room_name="Room Other", class_name="Physics 101")
        db.add(room_other)
        db.flush()
        sess_other = Session(classroom_id=room_other.id, status="Completed")
        db.add(sess_other)
        db.flush()

        # Link teacher ONLY to room_assigned
        db.add(TeacherClassroom(teacher_id=teacher.id, classroom_id=room_assigned.id))
        db.commit()
        db.close()

        headers = _auth(role="teacher", username="teacher_rep")

        # 1. List only includes assigned room session
        res_list = client.get("/reports", headers=headers)
        assert res_list.status_code == 200
        session_ids = [s["session_id"] for s in res_list.json()]
        assert sess_assigned.id in session_ids
        assert sess_other.id not in session_ids

        # 2. Detail on assigned session succeeds
        res_assigned = client.get(f"/reports/{sess_assigned.id}", headers=headers)
        assert res_assigned.status_code == 200

        # 3. Detail on unassigned session forbidden (403)
        res_forbidden = client.get(f"/reports/{sess_other.id}", headers=headers)
        assert res_forbidden.status_code == 403

        # 4. Export on unassigned session forbidden (403)
        res_exp_forbidden = client.get(f"/reports/{sess_other.id}/export?format=csv", headers=headers)
        assert res_exp_forbidden.status_code == 403

    def test_export_invalid_format_returns_422(self, client):
        db = TestSessionLocal()
        _seed_admin(db)
        _, sess = _seed_full_session(db)
        db.close()

        headers = _auth(role="admin", username="admin_rep")
        res = client.get(f"/reports/{sess.id}/export?format=docx", headers=headers)
        assert res.status_code == 422
