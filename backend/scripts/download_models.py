"""Download pretrained models into backend/models/ (decision D2)."""
import json
import os
import sys
from pathlib import Path
from huggingface_hub import HfApi, snapshot_download

BASE = Path(__file__).resolve().parents[1] / "models"
MODELS = {
    "drowsiness": "mosesb/drowsiness-detection-mobileViT-v2",
    "expression": "trpakov/vit-face-expression",
}


def main() -> int:
    BASE.mkdir(parents=True, exist_ok=True)
    manifest, failed = {}, []
    for name, repo_id in MODELS.items():
        target = BASE / name
        target.mkdir(parents=True, exist_ok=True)
        print(f"[download] {name}: {repo_id} -> {target}")
        try:
            snapshot_download(repo_id=repo_id, local_dir=str(target))
            info = HfApi().model_info(repo_id)
            license_val = None
            if info.card_data and hasattr(info.card_data, "license"):
                license_val = info.card_data.license
            elif hasattr(info, "tags"):
                for tag in info.tags:
                    if tag.startswith("license:"):
                        license_val = tag.split(":", 1)[1]
                        break

            manifest[name] = {
                "repo_id": repo_id,
                "revision": info.sha,  # pin for reproducibility
                "license": license_val,  # record for OQ-4
            }
        except Exception as e:
            print(f"[download] ERROR {name}: {e}")
            failed.append(name)

    manifest_path = BASE / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[download] manifest written: {manifest_path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
