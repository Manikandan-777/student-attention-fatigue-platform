"""MobileViT-v2 Drowsiness Classifier Wrapper.

Implements MDL-5, CON §2.1, CON §5 specifications:
- MobileViT-v2 inference under torch.inference_mode() and .eval().
- Batched inference for multi-face frames.
- Maps model outputs via canonical LABEL_MAP to {"label": "Drowsy" | "Non Drowsy", "p_drowsy": float}.
"""

from pathlib import Path
from typing import Any, Optional, Sequence
import numpy as np
import timm
import torch

DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "drowsiness"

# Single canonical mapping from raw model output labels to frozen contracts.md enums
LABEL_MAP: dict[str, str] = {
    "drowsy": "Drowsy",
    "non drowsy": "Non Drowsy",
    "nondrowsy": "Non Drowsy",
    "non-drowsy": "Non Drowsy",
    "alert": "Non Drowsy",
    "awake": "Non Drowsy",
    "0": "Drowsy",
    "1": "Non Drowsy",
}


def normalize_drowsiness_label(raw_label: str) -> str:
    """Normalize raw model prediction label into frozen contracts.md enum: 'Drowsy' or 'Non Drowsy'."""
    key = str(raw_label).strip().lower()
    if key in LABEL_MAP:
        return LABEL_MAP[key]
    raise ValueError(f"Unknown drowsiness label: '{raw_label}'. Expected one of {list(LABEL_MAP.keys())}")


class DrowsinessClassifier:
    """MobileViT-v2 deep learning inference wrapper for drowsiness prediction."""

    def __init__(
        self,
        model_dir: Optional[Path | str] = None,
        device: Optional[str] = None,
    ) -> None:
        self.model_dir = Path(model_dir) if model_dir else DEFAULT_MODEL_DIR
        self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))

        weights_file = None
        for cand in ["best_model.pt", "model.safetensors", "pytorch_model.bin"]:
            if (self.model_dir / cand).exists():
                weights_file = self.model_dir / cand
                break

        if not weights_file:
            raise FileNotFoundError(f"No weights file found in {self.model_dir}")

        # Instantiate MobileViT-v2 (mobilevitv2_200) architecture
        self.model = timm.create_model("mobilevitv2_200", pretrained=False, num_classes=2)

        if weights_file.suffix == ".safetensors":
            import safetensors.torch as st
            state_dict = st.load_file(str(weights_file))
        else:
            state_dict = torch.load(str(weights_file), map_location="cpu", weights_only=True)

        self.model.load_state_dict(state_dict)
        self.model.to(self.device)
        self.model.eval()

    def predict_batch(self, batch_tensor: torch.Tensor) -> list[dict[str, Any]]:
        """Run batched inference on (Batch, 3, 224, 224) normalized tensor.

        Returns:
            List of dicts: [{"label": "Drowsy"|"Non Drowsy", "p_drowsy": float}, ...]
        """
        if batch_tensor is None or batch_tensor.numel() == 0:
            return []

        if batch_tensor.device != self.device:
            batch_tensor = batch_tensor.to(self.device)

        with torch.inference_mode():
            logits = self.model(batch_tensor)
            probs = torch.softmax(logits, dim=1)

        results = []
        # Class 0: Drowsy, Class 1: Non Drowsy
        for i in range(probs.shape[0]):
            p_drowsy = float(probs[i, 0].item())
            # Binary decision threshold at 0.50
            if p_drowsy >= 0.50:
                label = "Drowsy"
            else:
                label = "Non Drowsy"

            results.append({
                "label": label,
                "p_drowsy": round(p_drowsy, 4),
            })

        return results

    def predict_single(self, tensor_3d: torch.Tensor) -> dict[str, Any]:
        """Convenience method for a single (3, 224, 224) tensor."""
        if tensor_3d.dim() == 3:
            tensor_4d = tensor_3d.unsqueeze(0)
        else:
            tensor_4d = tensor_3d
        batch_res = self.predict_batch(tensor_4d)
        return batch_res[0] if batch_res else {"label": "Non Drowsy", "p_drowsy": 0.0}
