"""Phase 4 Test Suite — Dynamic ROI Cropping, Alignment & Tensor Normalization.

Spec refs: MDL-5, SYS-5, implementation.md Phase 4.
Pass condition:
- Output shape is (Batch, 3, 224, 224) of dtype torch.float32.
- Normalization matches model preprocessor specs (MobileViT mean/std vs ViT mean/std).
- Invalid, tiny and out-of-frame crops are gracefully skipped without crashing.
"""

from pathlib import Path
import cv2
import numpy as np
import pytest
import torch

from ai.roi import (
    DEFAULT_DROWSINESS_NORM,
    DEFAULT_EXPRESSION_NORM,
    DEFAULT_MIN_FACE_PX,
    FaceROIExtractor,
    crop_face_roi,
    normalize_crop_to_tensor,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def extractor():
    return FaceROIExtractor()


@pytest.fixture
def sample_frame():
    # 640x480 synthetic test frame
    frame = np.full((480, 640, 3), 128, dtype=np.uint8)
    return frame


def test_roi_tensor_shape_and_dtype(extractor):
    """Assert output shape is (Batch, 3, 224, 224) and dtype is float32."""
    multi_frame_path = FIXTURES_DIR / "multi_face_frame.png"
    assert multi_frame_path.exists(), f"Missing fixture: {multi_frame_path}"
    frame = cv2.imread(str(multi_frame_path))

    # Two test bounding boxes [x, y, w, h] normalized
    tracks = [
        [0.125, 0.3125, 0.281, 0.375],  # Face 1 on left
        [0.593, 0.3125, 0.281, 0.375],  # Face 2 on right
    ]

    tensor_drow, valid_drow = extractor.prepare_drowsiness_batch(frame, tracks)
    assert tensor_drow.shape == (2, 3, 224, 224), f"Unexpected drowsiness shape: {tensor_drow.shape}"
    assert tensor_drow.dtype == torch.float32
    assert len(valid_drow) == 2

    tensor_expr, valid_expr = extractor.prepare_expression_batch(frame, tracks)
    assert tensor_expr.shape == (2, 3, 224, 224), f"Unexpected expression shape: {tensor_expr.shape}"
    assert tensor_expr.dtype == torch.float32
    assert len(valid_expr) == 2


def test_normalization_values_and_bounds():
    """Verify that normalization matches model preprocessors and satisfies expected bounds."""
    # Test 1: Expression normalization: mean = [0.5, 0.5, 0.5], std = [0.5, 0.5, 0.5]
    # Pure black (0, 0, 0) should normalize to -1.0
    black_rgb = np.zeros((224, 224, 3), dtype=np.uint8)
    t_black = normalize_crop_to_tensor(black_rgb, mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
    assert torch.allclose(t_black, torch.tensor(-1.0), atol=1e-4), f"Expected -1.0 for black, got {t_black[0,0,0]}"

    # Pure white (255, 255, 255) should normalize to +1.0
    white_rgb = np.full((224, 224, 3), 255, dtype=np.uint8)
    t_white = normalize_crop_to_tensor(white_rgb, mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
    assert torch.allclose(t_white, torch.tensor(1.0), atol=1e-3), f"Expected +1.0 for white, got {t_white[0,0,0]}"

    # Test 2: Drowsiness normalization (ImageNet stats)
    # mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
    test_pixel = np.array([[[124, 116, 104]]], dtype=np.uint8)  # 124/255 ~ 0.486, 116/255 ~ 0.455, 104/255 ~ 0.408
    test_rgb = np.tile(test_pixel, (224, 224, 1))
    t_drow = normalize_crop_to_tensor(
        test_rgb,
        mean=DEFAULT_DROWSINESS_NORM["mean"],
        std=DEFAULT_DROWSINESS_NORM["std"],
    )
    # Near zero for all 3 channels
    assert torch.all(torch.abs(t_drow.mean(dim=(1, 2))) < 0.05), "Normalized ImageNet values should center near zero"


def test_out_of_frame_boxes(sample_frame, extractor):
    """Verify that boxes partly outside frame are padded cleanly and completely outside are skipped."""
    # 1. Box partly outside top-left boundary (e.g. centered near corner)
    box_partly_out = [-0.05, -0.05, 0.3, 0.3]
    crop_partly = crop_face_roi(sample_frame, box_partly_out, is_normalized=True)
    assert crop_partly is not None, "Partly out-of-frame box should be padded and returned"
    assert crop_partly.shape == (224, 224, 3)

    # 2. Box partly outside bottom-right boundary
    box_partly_br = [0.85, 0.85, 0.3, 0.3]
    crop_br = crop_face_roi(sample_frame, box_partly_br, is_normalized=True)
    assert crop_br is not None
    assert crop_br.shape == (224, 224, 3)

    # 3. Box completely outside frame (e.g. negative or > 1.0 coordinates)
    box_completely_out = [-0.6, -0.6, 0.2, 0.2]
    crop_none = crop_face_roi(sample_frame, box_completely_out, is_normalized=True)
    assert crop_none is None, "Completely out-of-frame box must be rejected (return None)"

    box_completely_far = [1.5, 1.5, 0.2, 0.2]
    assert crop_face_roi(sample_frame, box_completely_far, is_normalized=True) is None


def test_tiny_face_rejection(sample_frame):
    """Verify that faces smaller than MIN_FACE_PX are rejected to avoid low-quality inference."""
    # Frame is 640x480. 10 pixels / 640 = 0.0156 width
    tiny_box = [0.5, 0.5, 0.015, 0.015]  # ~10x7 pixels (< 32px)
    crop_tiny = crop_face_roi(sample_frame, tiny_box, min_face_px=DEFAULT_MIN_FACE_PX)
    assert crop_tiny is None, f"Box below min_face_px ({DEFAULT_MIN_FACE_PX}) must be rejected"

    # Box just above threshold (e.g. 50x50 pixels -> 50/640 ~ 0.078, 50/480 ~ 0.104)
    valid_box = [0.4, 0.4, 0.10, 0.12]
    crop_valid = crop_face_roi(sample_frame, valid_box, min_face_px=DEFAULT_MIN_FACE_PX)
    assert crop_valid is not None, "Box above min_face_px should be accepted"


def test_batch_extractor_with_mixed_and_invalid_inputs(sample_frame, extractor):
    """Verify batch processing skips invalid crops without crashing and maintains index mapping."""
    mixed_tracks = [
        [0.2, 0.2, 0.25, 0.25],          # Valid face 0
        [-0.8, -0.8, 0.1, 0.1],          # Completely out of frame -> invalid
        [0.01, 0.01, 0.005, 0.005],      # Tiny face -> invalid
        [0.5, 0.4, 0.22, 0.25],          # Valid face 3
    ]

    tensor_batch, valid_tracks = extractor.prepare_drowsiness_batch(sample_frame, mixed_tracks)
    # Exactly 2 valid faces should be returned
    assert tensor_batch.shape == (2, 3, 224, 224)
    assert len(valid_tracks) == 2
    assert valid_tracks[0] == mixed_tracks[0]
    assert valid_tracks[1] == mixed_tracks[3]

    # Test completely empty input
    empty_tensor, empty_tracks = extractor.prepare_drowsiness_batch(sample_frame, [])
    assert empty_tensor.shape == (0, 3, 224, 224)
    assert len(empty_tracks) == 0

    # Test all-invalid input
    all_invalid = [[-1.0, -1.0, 0.1, 0.1], [2.0, 2.0, 0.1, 0.1]]
    zero_tensor, zero_tracks = extractor.prepare_expression_batch(sample_frame, all_invalid)
    assert zero_tensor.shape == (0, 3, 224, 224)
    assert len(zero_tracks) == 0
