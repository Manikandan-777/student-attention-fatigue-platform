"""Test Helper Script to Dispatch Class Fatigue Advisory Push Notification.

Implements README_MOBILE_ALERT_NOTIFICATIONS.md §7.6:
- Sends real push notification through Expo Push service to registered teacher devices.
- Strictly refuses to run when ENVIRONMENT=production.
- Does NOT expose HTTP endpoint (CLI / script only).
"""

import argparse
import asyncio
from datetime import datetime, timezone
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.db.database import SessionLocal
from app.db.models import Classroom, PushToken, Session as SessionModel
from app.notifications.advisory import ADVISORY_LEVELS
from app.notifications.expo_push import dispatch_advisory_push


def main() -> None:
    parser = argparse.ArgumentParser(description="Send test class fatigue advisory push notification.")
    parser.add_argument("--session", type=int, default=1, help="Session ID (default: 1)")
    parser.add_argument("--level", type=int, default=4, choices=[1, 2, 3, 4], help="Advisory level 1-4 (default: 4)")
    args = parser.parse_args()

    # Safety constraint: Refuse to run in production (§7.6)
    if settings.ENVIRONMENT.lower() == "production":
        print("ERROR: send_test_advisory.py cannot be executed in production environment.")
        sys.exit(1)

    db = SessionLocal()
    try:
        session_id = args.session
        level = args.level
        level_info = ADVISORY_LEVELS[level]

        # Fetch or default classroom name
        sess = db.get(SessionModel, session_id)
        class_name = "III AI & DS"
        if sess and sess.classroom_id:
            cr = db.get(Classroom, sess.classroom_id)
            if cr:
                class_name = cr.class_name or cr.room_name

        advisory_data = {
            "session_id": session_id,
            "class_name": class_name,
            "level": level,
            "code": level_info["code"],
            "message": level_info["message"],
            "since": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        print(f"[send_test_advisory] Target Session: {session_id} ({class_name})")
        print(f"[send_test_advisory] Level {level}: {level_info['code']} -> '{level_info['message']}'")

        # Check registered tokens in DB
        active_tokens = db.query(PushToken).filter_by(active=True).all()
        print(f"[send_test_advisory] Total active push tokens in database: {len(active_tokens)}")

        result = asyncio.run(dispatch_advisory_push(session_id, advisory_data, db))
        print(f"[send_test_advisory] Result: {result}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
