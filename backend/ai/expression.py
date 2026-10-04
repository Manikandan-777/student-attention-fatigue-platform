"""Vision Transformer (ViT) Facial Expression Classifier Wrapper.

Implements MDL-5, CON §1, CON §2.1, CON §6 specifications:
- ViT inference under torch.inference_mode() and .eval().
- Batched inference for multi-face frames.
- Output dictionary containing 'top' emotion and 'probs' with exactly the 7 frozen emotion keys:
  ['Angry', 'Disgust', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral'].
- Probabilities sum to 1.0 (+-1e-4).
"""

import json
from pathlib import Path
from typing import Any, Optional, Sequence
import numpy as np
import torch
from transformers import AutoModelForImageClassification

DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "expression"

# Canonical 7 emotions from contracts.md §1
CANONICAL_EMOTIONS = ["Angry", "Disgust", "Fear", "Happy", "Sad", "Surprise", "Neutral"]

EMOTION_MAP = {
    "angry": "Angry",
    "disgust": "Disgust",
    "fear": "Fear",
    "happy": "Happy",
    "sad": "Sad",
    "surprise": "Surprise",
    "neutral": "Neutral",
}


class ExpressionClassifier:
    """Vision Transformer deep learning inference wrapper for facial expression classification."""

    def __init__(
        self,
        model_dir: Optional[Path | str] = None,
        device: Optional[str] = None,
    ) -> None:
        self.model_dir = Path(model_dir) if model_dir else DEFAULT_MODEL_DIR
        self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))

        if not self.model_dir.exists():
            raise FileNotFoundError(f"Expression model directory not found at {self.model_dir}")

        # Load config and id2label
        cfg_file = self.model_dir / "config.json"
        with cfg_file.open("r", encoding="utf-8") as f:
            cfg = json.load(f)

        raw_id2label = cfg.get("id2label", {})
        # Map integer index -> canonical contracts.md emotion string
        self.idx2emotion: dict[int, str] = {}
        for idx_str, raw_label in raw_id2label.items():
            idx = int(idx_str)
            clean_key = str(raw_label).strip().lower()
            if clean_key in EMOTION_MAP:
                self.idx2emotion[idx] = EMOTION_MAP[clean_key]
            else:
                self.idx2emotion[idx] = str(raw_label).capitalize()

        # Load model weights
        self.model = AutoModelForImageClassification.from_pretrained(str(self.model_dir), local_files_only=True)  # nosec B615
        self.model.to(self.device)
        self.model.eval()

    def predict_batch(self, batch_tensor: torch.Tensor) -> list[dict[str, Any]]:
        """Run batched inference on (Batch, 3, 224, 224) normalized tensor.

        Returns:
            List of dicts: [
                {
                    "top": "Neutral",
                    "probs": {
                        "Angry": 0.01,
                        "Disgust": 0.0,
                        "Fear": 0.01,
                        "Happy": 0.1,
                        "Sad": 0.03,
                        "Surprise": 0.02,
                        "Neutral": 0.83
                    }
                }, ...
            ]
        """
        if batch_tensor is None or batch_tensor.numel() == 0:
            return []

        if batch_tensor.device != self.device:
            batch_tensor = batch_tensor.to(self.device)

        with torch.inference_mode():
            logits = self.model(batch_tensor).logits
            probs = torch.softmax(logits, dim=1)

        results = []
        batch_size = probs.shape[0]

        for i in range(batch_size):
            row_probs = probs[i].cpu().numpy()
            probs_dict: dict[str, float] = {}

            # Populate canonical emotion probabilities
            for idx, prob_val in enumerate(row_probs):
                emotion_name = self.idx2emotion.get(idx, f"Emotion_{idx}")
                probs_dict[emotion_name] = float(prob_val)

            # Ensure all 7 canonical emotions exist in probs_dict
            for emo in CANONICAL_EMOTIONS:
                if emo not in probs_dict:
                    probs_dict[emo] = 0.0

            # Normalize slightly if float precision causes sum deviation > 1e-4
            total = sum(probs_dict.values())
            if total > 0 and abs(total - 1.0) > 1e-5:
                for k in probs_dict:
                    probs_dict[k] = probs_dict[k] / total

            # Determine top emotion before rounding
            top_emotion = max(probs_dict.items(), key=lambda kv: kv[1])[0]

            # Round to 4 decimal places and adjust top emotion to ensure exact sum == 1.0
            rounded_probs = {k: round(v, 4) for k, v in probs_dict.items()}
            residual = round(1.0 - sum(rounded_probs.values()), 4)
            if residual != 0.0:
                rounded_probs[top_emotion] = round(rounded_probs[top_emotion] + residual, 4)

            results.append({
                "top": top_emotion,
                "probs": rounded_probs,
            })

        return results

    def predict_single(self, tensor_3d: torch.Tensor) -> dict[str, Any]:
        """Convenience method for a single (3, 224, 224) tensor."""
        if tensor_3d.dim() == 3:
            tensor_4d = tensor_3d.unsqueeze(0)
        else:
            tensor_4d = tensor_3d
        batch_res = self.predict_batch(tensor_4d)
        if batch_res:
            return batch_res[0]

        default_probs = {e: (1.0 if e == "Neutral" else 0.0) for e in CANONICAL_EMOTIONS}
        return {"top": "Neutral", "probs": default_probs}
