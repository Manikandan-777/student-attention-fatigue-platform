"""Session Report Builder & Exporters — Phase 16.

Implements SYS-13, APP-13/14, CON §8:
- Builds canonical session report JSON matching CON §8 schema.
- CSV export matching JSON aggregates exactly.
- PDF export (via ReportLab) matching JSON aggregates exactly.
- Mandatory legal footer on all formats:
  "AI-generated indicators to support teacher observation; not a diagnosis or disciplinary record."
"""

import csv
import html
import io
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session as DBSession

from app.db.models import Alert, Observation, Session

MANDATORY_FOOTER = "AI-generated indicators to support teacher observation; not a diagnosis or disciplinary record."


def build_session_report(db: DBSession, session_id: int) -> Dict[str, Any]:
    """Generate canonical session report JSON according to contracts.md §8."""
    session = db.get(Session, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found.")

    class_name = session.classroom.class_name if session.classroom else "Classroom"
    started = session.started_at
    ended = session.ended_at or session.started_at

    duration_min = max(1, int((ended - started).total_seconds() / 60))

    # Fetch observations & alerts
    observations = (
        db.query(Observation)
        .filter(Observation.session_id == session_id)
        .order_by(Observation.ts.asc())
        .all()
    )
    alerts = (
        db.query(Alert)
        .filter(Alert.session_id == session_id)
        .all()
    )

    # Group observations by track_id
    by_track: Dict[int, List[Observation]] = {}
    for obs in observations:
        by_track.setdefault(obs.track_id, []).append(obs)

    # Determine unique track IDs
    track_ids = sorted(by_track.keys())
    students_count = max(len(track_ids), session.students_detected_max)

    # Aggregates
    attentive_count = 0
    distracted_count = 0
    unknown_count = 0
    normal_count = 0
    fatigued_count = 0

    per_student: List[Dict[str, Any]] = []
    all_attention_means: List[float] = []

    for tid in track_ids:
        track_obs = by_track[tid]
        label = f"S{tid:03d}"

        # Indicators counts
        fatigue_ind = sum(1 for o in track_obs if o.fatigue_status == "Fatigued")
        distraction_ind = sum(1 for o in track_obs if o.attention_status == "Distracted")
        track_alerts = sum(1 for a in alerts if a.track_id == tid)

        # Means
        att_scores = [o.attention_score_mean for o in track_obs if o.total_frames > 0]
        fat_indices = [o.fatigue_index_mean for o in track_obs if o.total_frames > 0]

        att_mean = round(float(sum(att_scores) / len(att_scores)), 1) if att_scores else 0.0
        fat_mean = round(float(sum(fat_indices) / len(fat_indices)), 2) if fat_indices else 0.0

        if att_scores:
            all_attention_means.append(att_mean)

        # State classification for the student (based on predominant or latest state)
        last_obs = track_obs[-1]
        if last_obs.attention_status == "Attentive":
            attentive_count += 1
        elif last_obs.attention_status == "Distracted":
            distracted_count += 1
        else:
            unknown_count += 1

        if fatigue_ind > 0 or last_obs.fatigue_status == "Fatigued":
            fatigued_count += 1
        else:
            normal_count += 1

        per_student.append({
            "label": label,
            "attention_mean": att_mean,
            "fatigue_index_mean": fat_mean,
            "fatigue_indicators": fatigue_ind,
            "distraction_indicators": distraction_ind,
            "alerts": track_alerts,
        })

    # If students_detected_max was larger than active tracks with observations
    remaining_students = students_count - len(track_ids)
    if remaining_students > 0:
        unknown_count += remaining_students
        normal_count += remaining_students

    avg_attention_score = (
        round(float(sum(all_attention_means) / len(all_attention_means)), 1)
        if all_attention_means
        else 0.0
    )

    return {
        "session_id": session.id,
        "class_name": class_name,
        "date": started.strftime("%Y-%m-%d"),
        "start": started.strftime("%H:%M"),
        "end": ended.strftime("%H:%M"),
        "duration_min": duration_min,
        "students": students_count,
        "attention": {
            "attentive": attentive_count,
            "distracted": distracted_count,
            "unknown": unknown_count,
        },
        "fatigue": {
            "normal": normal_count,
            "fatigued": fatigued_count,
        },
        "alerts_total": len(alerts),
        "avg_attention_score": avg_attention_score,
        "per_student": per_student,
    }


def _escape_csv_cell(val: Any) -> Any:
    """Neutralize formula injection by prefixing with a single quote (EXP1)."""
    if isinstance(val, str) and val and val[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{val}"
    return val


def export_csv(report: Dict[str, Any]) -> str:
    """Export session report to CSV format with exact aggregate matching, footer, and injection defense."""
    output = io.StringIO()
    writer = csv.writer(output)

    # 1. Header Metadata
    writer.writerow(["Session Report", report["session_id"]])
    writer.writerow(["Class Name", _escape_csv_cell(report["class_name"])])
    writer.writerow(["Date", report["date"]])
    writer.writerow(["Start Time", report["start"]])
    writer.writerow(["End Time", report["end"]])
    writer.writerow(["Duration (min)", report["duration_min"]])
    writer.writerow(["Total Students", report["students"]])
    writer.writerow(["Alerts Total", report["alerts_total"]])
    writer.writerow(["Average Attention Score", report["avg_attention_score"]])
    writer.writerow([])

    # 2. Aggregates
    writer.writerow(["Attention Breakdown"])
    writer.writerow(["Attentive", report["attention"]["attentive"]])
    writer.writerow(["Distracted", report["attention"]["distracted"]])
    writer.writerow(["Unknown", report["attention"]["unknown"]])
    writer.writerow([])

    writer.writerow(["Fatigue Breakdown"])
    writer.writerow(["Normal", report["fatigue"]["normal"]])
    writer.writerow(["Fatigued", report["fatigue"]["fatigued"]])
    writer.writerow([])

    # 3. Per Student Table
    writer.writerow([
        "Student Label",
        "Attention Mean",
        "Fatigue Index Mean",
        "Fatigue Indicators",
        "Distraction Indicators",
        "Alerts",
    ])
    for st in report.get("per_student", []):
        writer.writerow([
            _escape_csv_cell(st["label"]),
            st["attention_mean"],
            st["fatigue_index_mean"],
            st["fatigue_indicators"],
            st["distraction_indicators"],
            st["alerts"],
        ])
    writer.writerow([])

    # 4. Mandatory Footer (D8)
    writer.writerow([MANDATORY_FOOTER])

    return output.getvalue()


def export_pdf(report: Dict[str, Any]) -> bytes:
    """Generate session report PDF with exact aggregate matching and footer."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    subtitle_style = styles["Heading2"]
    normal_style = styles["Normal"]

    footer_style = ParagraphStyle(
        "FooterStyle",
        parent=styles["Italic"],
        fontSize=8,
        textColor=colors.gray,
        alignment=1,  # Centered
    )

    story = []

    # Title (escaped against XSS/malformed tags)
    clean_class_name = html.escape(str(report.get("class_name", "Classroom")))
    story.append(Paragraph(f"Classroom Analytics Report: {clean_class_name}", title_style))
    story.append(Spacer(1, 12))

    # Metadata Table
    meta_data = [
        ["Session ID", str(report["session_id"]), "Date", str(report["date"])],
        ["Start Time", str(report["start"]), "End Time", str(report["end"])],
        ["Duration (min)", str(report["duration_min"]), "Total Students", str(report["students"])],
        ["Avg Attention Score", f"{report['avg_attention_score']}%", "Alerts Total", str(report["alerts_total"])],
    ]
    meta_table = Table(meta_data, colWidths=[120, 140, 120, 140])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # Breakdown Aggregates Table
    story.append(Paragraph("Engagement & Fatigue Summary", subtitle_style))
    agg_data = [
        ["Attention State", "Count", "Fatigue State", "Count"],
        ["Attentive", str(report["attention"]["attentive"]), "Normal", str(report["fatigue"]["normal"])],
        ["Distracted", str(report["attention"]["distracted"]), "Fatigued", str(report["fatigue"]["fatigued"])],
        ["Unknown", str(report["attention"]["unknown"]), "", ""],
    ]
    agg_table = Table(agg_data, colWidths=[130, 130, 130, 130])
    agg_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.navy),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(agg_table)
    story.append(Spacer(1, 16))

    # Per-Student Table
    story.append(Paragraph("Per-Student Breakdown", subtitle_style))
    student_rows = [
        ["Label", "Attention Mean", "Fatigue Index", "Fatigue Ind.", "Distraction Ind.", "Alerts"]
    ]
    for s in report.get("per_student", []):
        student_rows.append([
            html.escape(str(s["label"])),
            f"{s['attention_mean']}%",
            f"{s['fatigue_index_mean']}",
            str(s["fatigue_indicators"]),
            str(s["distraction_indicators"]),
            str(s["alerts"]),
        ])

    student_table = Table(student_rows, colWidths=[80, 90, 85, 85, 95, 85])
    student_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
    ]))
    story.append(student_table)
    story.append(Spacer(1, 24))

    # Mandatory Legal Footer (D8)
    story.append(Paragraph(MANDATORY_FOOTER, footer_style))

    doc.build(story)
    return buffer.getvalue()
