"""Facial feature extraction from MediaPipe landmarks (EAR, MAR, Head Pose).

Implements SYS-4, CON §2.1 specifications:
- Eye Aspect Ratio (EAR) for blink and closure detection.
- Mouth Aspect Ratio (MAR) for yawn detection.
- Head Pose (yaw, pitch) via 3D landmarks and solvePnP for off-task attention detection.
"""

from typing import Any, Sequence
import cv2
import numpy as np

# MediaPipe Face Mesh landmark indices
# Left eye
LEFT_EYE_OUTER = 33
LEFT_EYE_INNER = 133
LEFT_EYE_TOP1 = 160
LEFT_EYE_BOTTOM1 = 144
LEFT_EYE_TOP2 = 158
LEFT_EYE_BOTTOM2 = 153

# Right eye
RIGHT_EYE_INNER = 362
RIGHT_EYE_OUTER = 263
RIGHT_EYE_TOP1 = 385
RIGHT_EYE_BOTTOM1 = 380
RIGHT_EYE_TOP2 = 387
RIGHT_EYE_BOTTOM2 = 373

# Mouth
MOUTH_LEFT = 61
MOUTH_RIGHT = 291
MOUTH_TOP_MID = 13
MOUTH_BOTTOM_MID = 14
MOUTH_TOP_LEFT = 81
MOUTH_BOTTOM_LEFT = 178
MOUTH_TOP_RIGHT = 311
MOUTH_BOTTOM_RIGHT = 402

# Head pose 3D canonical face model coordinates
CANONICAL_FACE_3D = np.array([
    (0.0, 0.0, 0.0),          # Nose tip (index 1)
    (0.0, -330.0, -65.0),     # Chin (index 152)
    (-225.0, 170.0, -135.0),  # Left eye outer corner (index 33)
    (225.0, 170.0, -135.0),   # Right eye outer corner (index 263)
    (-150.0, -150.0, -125.0), # Left mouth corner (index 61)
    (150.0, -150.0, -125.0),  # Right mouth corner (index 291)
], dtype=np.float64)

POSE_LANDMARK_INDICES = [1, 152, 33, 263, 61, 291]


def _euclidean_distance(p1: Sequence[float], p2: Sequence[float]) -> float:
    return float(np.linalg.norm(np.array(p1[:2]) - np.array(p2[:2])))


def calculate_eye_aspect_ratio(landmarks: Sequence[Any]) -> float:
    """Compute Eye Aspect Ratio (EAR) averaged across both eyes.

    EAR decreases as eyes close. Typical open eye EAR: 0.25 - 0.38, closed: < 0.18.
    """
    def _ear_single_eye(outer: int, inner: int, t1: int, b1: int, t2: int, b2: int) -> float:
        p_outer = (landmarks[outer].x, landmarks[outer].y)
        p_inner = (landmarks[inner].x, landmarks[inner].y)
        p_t1 = (landmarks[t1].x, landmarks[t1].y)
        p_b1 = (landmarks[b1].x, landmarks[b1].y)
        p_t2 = (landmarks[t2].x, landmarks[t2].y)
        p_b2 = (landmarks[b2].x, landmarks[b2].y)

        horizontal = _euclidean_distance(p_outer, p_inner)
        if horizontal <= 1e-6:
            return 0.0

        v1 = _euclidean_distance(p_t1, p_b1)
        v2 = _euclidean_distance(p_t2, p_b2)
        return (v1 + v2) / (2.0 * horizontal)

    ear_left = _ear_single_eye(
        LEFT_EYE_OUTER, LEFT_EYE_INNER,
        LEFT_EYE_TOP1, LEFT_EYE_BOTTOM1,
        LEFT_EYE_TOP2, LEFT_EYE_BOTTOM2,
    )
    ear_right = _ear_single_eye(
        RIGHT_EYE_OUTER, RIGHT_EYE_INNER,
        RIGHT_EYE_TOP1, RIGHT_EYE_BOTTOM1,
        RIGHT_EYE_TOP2, RIGHT_EYE_BOTTOM2,
    )

    return float((ear_left + ear_right) / 2.0)


def calculate_mouth_aspect_ratio(landmarks: Sequence[Any]) -> float:
    """Compute Mouth Aspect Ratio (MAR) to detect yawning / open mouth.

    MAR increases when mouth opens wide. Normal: ~0.15 - 0.35, Yawn: > 0.60.
    """
    p_left = (landmarks[MOUTH_LEFT].x, landmarks[MOUTH_LEFT].y)
    p_right = (landmarks[MOUTH_RIGHT].x, landmarks[MOUTH_RIGHT].y)
    horizontal = _euclidean_distance(p_left, p_right)
    if horizontal <= 1e-6:
        return 0.0

    p_t_mid = (landmarks[MOUTH_TOP_MID].x, landmarks[MOUTH_TOP_MID].y)
    p_b_mid = (landmarks[MOUTH_BOTTOM_MID].x, landmarks[MOUTH_BOTTOM_MID].y)
    p_t_l = (landmarks[MOUTH_TOP_LEFT].x, landmarks[MOUTH_TOP_LEFT].y)
    p_b_l = (landmarks[MOUTH_BOTTOM_LEFT].x, landmarks[MOUTH_BOTTOM_LEFT].y)
    p_t_r = (landmarks[MOUTH_TOP_RIGHT].x, landmarks[MOUTH_TOP_RIGHT].y)
    p_b_r = (landmarks[MOUTH_BOTTOM_RIGHT].x, landmarks[MOUTH_BOTTOM_RIGHT].y)

    v_mid = _euclidean_distance(p_t_mid, p_b_mid)
    v_l = _euclidean_distance(p_t_l, p_b_l)
    v_r = _euclidean_distance(p_t_r, p_b_r)

    vertical = (v_mid + v_l + v_r) / 3.0
    return float(vertical / horizontal)


def calculate_head_pose(landmarks: Sequence[Any], image_width: int = 640, image_height: int = 480) -> tuple[float, float, float]:
    """Estimate head orientation angles (yaw, pitch, roll in degrees) via solvePnP.

    Returns:
        (yaw, pitch, roll) in degrees.
        Yaw: negative = looking left, positive = looking right
        Pitch: negative = looking down, positive = looking up
    """
    image_points = []
    for idx in POSE_LANDMARK_INDICES:
        lm = landmarks[idx]
        image_points.append((lm.x * image_width, lm.y * image_height))
    image_points_np = np.array(image_points, dtype=np.float64)

    # Approximate camera intrinsic matrix
    focal_length = image_width
    center = (image_width / 2.0, image_height / 2.0)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype=np.float64)

    dist_coeffs = np.zeros((4, 1), dtype=np.float64)  # Assume no lens distortion

    success, rotation_vector, translation_vector = cv2.solvePnP(
        CANONICAL_FACE_3D,
        image_points_np,
        camera_matrix,
        dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )

    if not success:
        return 0.0, 0.0, 0.0

    rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
    # RQDecomp3x3 returns (euler_angles, mtxR, mtxQ, Qx, Qy, Qz)
    rq_res = cv2.RQDecomp3x3(rotation_matrix)
    euler_angles = rq_res[0]

    pitch = float(euler_angles[0])
    yaw = float(euler_angles[1])
    roll = float(euler_angles[2])

    return yaw, pitch, roll


def extract_features(landmarks: Sequence[Any], image_width: int = 640, image_height: int = 480) -> dict[str, float]:
    """Extract full feature set conforming to contracts.md §2.1 TrackResult.features schema."""
    ear = calculate_eye_aspect_ratio(landmarks)
    mar = calculate_mouth_aspect_ratio(landmarks)
    yaw, pitch, _ = calculate_head_pose(landmarks, image_width=image_width, image_height=image_height)

    return {
        "ear": round(ear, 4),
        "mar": round(mar, 4),
        "head_yaw": round(yaw, 2),
        "head_pitch": round(pitch, 2),
    }
