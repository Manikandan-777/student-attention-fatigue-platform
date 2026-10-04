"""Dynamic ROI Cropping, Alignment and Batch Tensor Preprocessing.

Implements MDL-5, SYS-5 specifications:
- Dynamic margin expansion around tracked facial bounding boxes.
- Graceful handling of out-of-frame boxes (clamping/padding).
- Gating and rejection of tiny faces below MIN_FACE_PX.
- Normalization tailored to preprocessor_config.json of Drowsiness (MobileViT-v2)
  and Expression (ViT) models.
- Returns batched PyTorch tensors (Batch, 3, 224, 224) with tracking index alignment.
"""

import json
from pathlib import Path
from typing import Any, Optional, Sequence
import cv2
import numpy as np
import torch

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"

# Configurable defaults (contract thresholds)
DEFAULT_MIN_FACE_PX = 32
DEFAULT_MARGIN = 0.15
DEFAULT_IMAGE_SIZE = (224, 224)

# Preprocessor fallback specs matching MDL-4
DEFAULT_DROWSINESS_NORM = {
    "size": (224, 224),
    "mean": [0.485, 0.456, 0.406],
    "std": [0.229, 0.224, 0.225],
}

DEFAULT_EXPRESSION_NORM = {
    "size": (224, 224),
    "mean": [0.5, 0.5, 0.5],
    "std": [0.5, 0.5, 0.5],
}


def load_preprocessor_specs(model_dir: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    """Load image size, mean and std from a model's preprocessor_config.json."""
    prep_file = model_dir / "preprocessor_config.json"
    if not prep_file.exists():
        return fallback

    try:
        with prep_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract size
        size_raw = data.get("size", fallback["size"])
        if isinstance(size_raw, dict):
            h = size_raw.get("height", 224)
            w = size_raw.get("width", 224)
            size = (w, h)
        elif isinstance(size_raw, int):
            size = (size_raw, size_raw)
        elif isinstance(size_raw, (list, tuple)):
            size = (int(size_raw[0]), int(size_raw[1]))
        else:
            size = fallback["size"]

        mean = data.get("image_mean", fallback["mean"])
        std = data.get("image_std", fallback["std"])

        return {
            "size": size,
            "mean": [float(m) for m in mean],
            "std": [float(s) for s in std],
        }
    except Exception:
        return fallback


def crop_face_roi(
    frame_bgr: np.ndarray,
    bbox: Sequence[float],
    is_normalized: bool = True,
    margin: float = DEFAULT_MARGIN,
    min_face_px: int = DEFAULT_MIN_FACE_PX,
    target_size: tuple[int, int] = DEFAULT_IMAGE_SIZE,
) -> Optional[np.ndarray]:
    """Crop, pad, and resize a face region of interest.

    Args:
        frame_bgr: Source image (H, W, 3) in BGR format.
        bbox: [x, y, w, h] bounding box.
        is_normalized: If True, bbox is in [0, 1] relative coordinates.
        margin: Fraction by which to expand the box (e.g. 0.15 for 15%).
        min_face_px: Minimum width and height in pixels. Smaller faces return None.
        target_size: Target (width, height) for resized crop.

    Returns:
        RGB image of shape (target_h, target_w, 3) with dtype uint8, or None if invalid.
    """
    if frame_bgr is None or frame_bgr.size == 0:
        return None

    img_h, img_w = frame_bgr.shape[:2]
    if img_h <= 0 or img_w <= 0:
        return None

    # Convert bbox to pixel coordinates
    bx, by, bw, bh = bbox[:4]
    if is_normalized:
        x_px = bx * img_w
        y_px = by * img_h
        w_px = bw * img_w
        h_px = bh * img_h
    else:
        x_px, y_px, w_px, h_px = float(bx), float(by), float(bw), float(bh)

    # Reject tiny faces below MIN_FACE_PX
    if w_px < min_face_px or h_px < min_face_px:
        return None

    # Apply margin expansion
    mx = w_px * margin
    my = h_px * margin

    x1 = int(round(x_px - mx))
    y1 = int(round(y_px - my))
    x2 = int(round(x_px + w_px + mx))
    y2 = int(round(y_px + h_px + my))

    crop_w = x2 - x1
    crop_h = y2 - y1
    if crop_w <= 0 or crop_h <= 0:
        return None

    # Handle boundary conditions (box partly or entirely outside the frame)
    # Determine valid intersection inside frame
    ix1 = max(0, x1)
    iy1 = max(0, y1)
    ix2 = min(img_w, x2)
    iy2 = min(img_h, y2)

    inter_w = ix2 - ix1
    inter_h = iy2 - iy1

    # If completely outside or zero intersection, reject
    if inter_w <= 0 or inter_h <= 0:
        return None

    # If the intersection is smaller than min_face_px, reject
    if inter_w < min_face_px or inter_h < min_face_px:
        return None

    # Create padded crop canvas matching requested (crop_h, crop_w)
    # Padded with border replicate or reflection to prevent black-edge artifacts
    if ix1 == x1 and iy1 == y1 and ix2 == x2 and iy2 == y2:
        crop_bgr = frame_bgr[y1:y2, x1:x2]
    else:
        # Border clamp extraction with replicate padding
        pad_top = max(0, -y1)
        pad_bottom = max(0, y2 - img_h)
        pad_left = max(0, -x1)
        pad_right = max(0, x2 - img_w)

        valid_region = frame_bgr[iy1:iy2, ix1:ix2]
        crop_bgr = cv2.copyMakeBorder(
            valid_region,
            top=pad_top,
            bottom=pad_bottom,
            left=pad_left,
            right=pad_right,
            borderType=cv2.BORDER_REPLICATE,
        )

    # Convert to RGB and resize to target size
    crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
    resized_rgb = cv2.resize(crop_rgb, target_size, interpolation=cv2.INTER_LINEAR)
    return resized_rgb


def normalize_crop_to_tensor(
    crop_rgb: np.ndarray,
    mean: Sequence[float],
    std: Sequence[float],
) -> torch.Tensor:
    """Normalize a uint8 RGB image to a (3, H, W) float32 PyTorch tensor.

    Formula: tensor = ((crop / 255.0) - mean) / std
    """
    img_float = crop_rgb.astype(np.float32) / 255.0
    mean_arr = np.array(mean, dtype=np.float32).reshape(1, 1, 3)
    std_arr = np.array(std, dtype=np.float32).reshape(1, 1, 3)

    norm_img = (img_float - mean_arr) / std_arr
    # HWC -> CHW
    tensor = torch.from_numpy(norm_img.transpose(2, 0, 1))
    return tensor


class FaceROIExtractor:
    """Extracts, aligns, and batches face crops for downstream PyTorch inference models."""

    def __init__(
        self,
        min_face_px: int = DEFAULT_MIN_FACE_PX,
        margin: float = DEFAULT_MARGIN,
        models_base_dir: Optional[Path] = None,
    ) -> None:
        self.min_face_px = min_face_px
        self.margin = margin
        base = models_base_dir or MODELS_DIR

        self.drowsiness_specs = load_preprocessor_specs(base / "drowsiness", DEFAULT_DROWSINESS_NORM)
        self.expression_specs = load_preprocessor_specs(base / "expression", DEFAULT_EXPRESSION_NORM)

    def extract_crops(
        self,
        frame_bgr: np.ndarray,
        tracks: Sequence[Any],
        target_size: tuple[int, int] = DEFAULT_IMAGE_SIZE,
    ) -> list[tuple[int, Any, np.ndarray]]:
        """Extract valid face crops for all tracks in a frame.

        Returns:
            List of tuples: (original_index, track_or_box, crop_rgb_uint8)
        """
        valid_crops = []
        for idx, item in enumerate(tracks):
            # item can be TrackedFace or a raw bbox sequence
            bbox = getattr(item, "bbox", item)
            crop = crop_face_roi(
                frame_bgr=frame_bgr,
                bbox=bbox,
                is_normalized=True,
                margin=self.margin,
                min_face_px=self.min_face_px,
                target_size=target_size,
            )
            if crop is not None:
                valid_crops.append((idx, item, crop))
        return valid_crops

    def prepare_drowsiness_batch(
        self,
        frame_bgr: np.ndarray,
        tracks: Sequence[Any],
    ) -> tuple[torch.Tensor, list[Any]]:
        """Prepare batched (Batch, 3, 224, 224) tensor for MobileViT-v2 drowsiness classifier.

        Returns:
            (batch_tensor, valid_tracks_list)
        """
        target_size = self.drowsiness_specs["size"]
        crops = self.extract_crops(frame_bgr, tracks, target_size=target_size)

        if not crops:
            empty_tensor = torch.empty((0, 3, target_size[1], target_size[0]), dtype=torch.float32)
            return empty_tensor, []

        tensors = []
        valid_items = []
        mean = self.drowsiness_specs["mean"]
        std = self.drowsiness_specs["std"]

        for _, item, crop_rgb in crops:
            t = normalize_crop_to_tensor(crop_rgb, mean=mean, std=std)
            tensors.append(t)
            valid_items.append(item)

        batch_tensor = torch.stack(tensors, dim=0)
        return batch_tensor, valid_items

    def prepare_expression_batch(
        self,
        frame_bgr: np.ndarray,
        tracks: Sequence[Any],
    ) -> tuple[torch.Tensor, list[Any]]:
        """Prepare batched (Batch, 3, 224, 224) tensor for ViT facial expression classifier.

        Returns:
            (batch_tensor, valid_tracks_list)
        """
        target_size = self.expression_specs["size"]
        crops = self.extract_crops(frame_bgr, tracks, target_size=target_size)

        if not crops:
            empty_tensor = torch.empty((0, 3, target_size[1], target_size[0]), dtype=torch.float32)
            return empty_tensor, []

        tensors = []
        valid_items = []
        mean = self.expression_specs["mean"]
        std = self.expression_specs["std"]

        for _, item, crop_rgb in crops:
            t = normalize_crop_to_tensor(crop_rgb, mean=mean, std=std)
            tensors.append(t)
            valid_items.append(item)

        batch_tensor = torch.stack(tensors, dim=0)
        return batch_tensor, valid_items
