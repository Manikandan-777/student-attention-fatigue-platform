"""Generate test fixtures for Phase 3 tracker and feature tests."""

from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import cv2
import numpy as np

from ai.features import calculate_eye_aspect_ratio
from ai.mediapipe_tracker import MultiFaceTracker

SCRIPT_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = SCRIPT_DIR / "fixtures"
MODELS_DIR = SCRIPT_DIR.parent / "models"


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    sample_img_path = MODELS_DIR / "drowsiness" / "output.png"
    if not sample_img_path.exists():
        raise FileNotFoundError(f"Source image not found: {sample_img_path}")

    img = cv2.imread(str(sample_img_path))
    h, w = img.shape[:2]

    tracker = MultiFaceTracker()
    tracks = tracker.process_frame(img)
    print(f"Detected {len(tracks)} faces in sample image.")

    # Find highest EAR (open eyes) and lowest EAR (closed eyes) faces
    open_face = max(tracks, key=lambda t: t.features["ear"])
    closed_face = min(tracks, key=lambda t: t.features["ear"])

    print(f"Open eye candidate: {open_face.label} with EAR={open_face.features['ear']}")
    print(f"Closed eye candidate: {closed_face.label} with EAR={closed_face.features['ear']}")

    def crop_face(trk, margin=0.15):
        bx, by, bw, bh = trk.pixel_bbox
        mx = int(bw * margin)
        my = int(bh * margin)
        x1 = max(0, bx - mx)
        y1 = max(0, by - my)
        x2 = min(w, bx + bw + mx)
        y2 = min(h, by + bh + my)
        return img[y1:y2, x1:x2]

    crop_open = crop_face(open_face)
    crop_closed = crop_face(closed_face)

    cv2.imwrite(str(FIXTURES_DIR / "face_open_eyes.png"), crop_open)
    cv2.imwrite(str(FIXTURES_DIR / "face_closed_eyes.png"), crop_closed)
    print("Saved face_open_eyes.png and face_closed_eyes.png")

    # Create a 2-face composite image (640x480)
    canvas = np.zeros((480, 640, 3), dtype=np.uint8)
    face1 = cv2.resize(crop_open, (180, 180))
    face2 = cv2.resize(crop_closed, (180, 180))

    # Place face 1 on left, face 2 on right
    canvas[150:330, 80:260] = face1
    canvas[150:330, 380:560] = face2
    cv2.imwrite(str(FIXTURES_DIR / "multi_face_frame.png"), canvas)
    print("Saved multi_face_frame.png")

    # Create a 15-frame video clip sequence with subtle realistic movement
    clip_dir = FIXTURES_DIR / "clip"
    clip_dir.mkdir(parents=True, exist_ok=True)

    for frame_idx in range(15):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Small sine-wave movement (simulating natural head movement of students)
        dx1 = int(3 * np.sin(frame_idx * 0.4))
        dy1 = int(2 * np.cos(frame_idx * 0.4))
        dx2 = int(3 * np.cos(frame_idx * 0.4))
        dy2 = int(2 * np.sin(frame_idx * 0.4))

        x1_pos = 80 + dx1
        y1_pos = 150 + dy1
        x2_pos = 380 + dx2
        y2_pos = 150 + dy2

        frame[y1_pos:y1_pos + 180, x1_pos:x1_pos + 180] = face1
        frame[y2_pos:y2_pos + 180, x2_pos:x2_pos + 180] = face2

        cv2.imwrite(str(clip_dir / f"frame_{frame_idx:03d}.png"), frame)

    print(f"Generated 15 consecutive clip frames in {clip_dir}")


if __name__ == "__main__":
    main()
