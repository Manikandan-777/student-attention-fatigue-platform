#!/usr/bin/env python3
"""Environment Verification Script for Phase 1.

Imports every required core dependency, asserts installed package versions against
requirements.txt, and prints Python runtime environment and CUDA availability.
"""

from importlib.metadata import version as get_meta_version
from pathlib import Path
import sys

# Define mapping between package names in requirements.txt and their import names
REQUIRED_PACKAGES = {
    "torch": "torch",
    "torchvision": "torchvision",
    "transformers": "transformers",
    "mediapipe": "mediapipe",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "opencv-python": "cv2",
    "huggingface_hub": "huggingface_hub",
    "sqlalchemy": "sqlalchemy",
    "pytest": "pytest",
    "pytest-asyncio": "pytest_asyncio",
    "httpx": "httpx",
}


def load_requirements_pins(req_path: Path) -> dict[str, str]:
    pins = {}
    if not req_path.exists():
        raise FileNotFoundError(f"requirements.txt not found at {req_path}")

    with req_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "==" in line:
                pkg, ver = line.split("==", 1)
                # Normalize key to lower-case and replace _ with -
                clean_pkg = pkg.strip().lower().replace("_", "-")
                pins[clean_pkg] = ver.strip()
    return pins


def main() -> int:
    print("=" * 60)
    print("Phase 1 — Environment & Dependency Verification")
    print("=" * 60)

    # 1. Python runtime information
    print(f"[Python] Version: {sys.version}")
    print(f"[Python] Executable: {sys.executable}")

    # Determine requirements.txt location
    script_dir = Path(__file__).resolve().parent
    backend_dir = script_dir.parent
    req_file = backend_dir / "requirements.txt"

    print(f"[Config] Reading requirements from: {req_file}")
    pins = load_requirements_pins(req_file)

    # 2. Import check and version assertions
    errors = []
    print("\n--- Verifying Package Imports & Version Assertions ---")
    for req_name, import_name in REQUIRED_PACKAGES.items():
        norm_req_name = req_name.lower().replace("_", "-")
        pinned_version = pins.get(norm_req_name)

        # Import test
        try:
            mod = __import__(import_name)
            installed_version = get_meta_version(req_name)
            print(
                f"[OK] {req_name:<18} imported (module: {import_name:<14}) | version: {installed_version}"
            )
        except ImportError as e:
            err = f"Failed to import '{import_name}' (package '{req_name}'): {e}"
            print(f"[FAIL] {err}")
            errors.append(err)
            continue
        except Exception as e:
            err = f"Error inspecting package '{req_name}': {e}"
            print(f"[FAIL] {err}")
            errors.append(err)
            continue

        # Version assertion against requirements.txt
        if pinned_version:
            if installed_version != pinned_version:
                err = f"Version mismatch for {req_name}: installed '{installed_version}' != pinned '{pinned_version}'"
                print(f"  --> [ASSERTION FAIL] {err}")
                errors.append(err)
            else:
                print(f"  --> [ASSERTION PASS] Matches requirements.txt pin ({pinned_version})")
        else:
            print(f"  --> [WARN] '{req_name}' not pinned in requirements.txt")

    # 3. CUDA Availability & Hardware status
    print("\n--- Hardware & Accelerator Status ---")
    try:
        import torch

        cuda_available = torch.cuda.is_available()
        print(f"[PyTorch] CUDA available: {cuda_available}")
        if cuda_available:
            print(f"[PyTorch] Device name: {torch.cuda.get_device_name(0)}")
            print(f"[PyTorch] Device count: {torch.cuda.device_count()}")
        else:
            print("[PyTorch] Target device: CPU (Hardware declared as CPU only)")
    except Exception as e:
        err = f"Error querying PyTorch CUDA status: {e}"
        print(f"[FAIL] {err}")
        errors.append(err)

    print("\n" + "=" * 60)
    if errors:
        print(f"Verification FAILED with {len(errors)} error(s):")
        for err in errors:
            print(f" - {err}")
        print("=" * 60)
        return 1

    print("Verification PASSED: All packages imported and pinned versions verified.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
