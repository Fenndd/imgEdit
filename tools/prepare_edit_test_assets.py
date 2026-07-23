"""Prepare non-personal local input and mask assets for the FLUX.2 edit tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ComfyUI" / "output" / "FLUX2_KLEIN_GGUF_T2I_40STEP_00001_.png"
INPUT_DIR = ROOT / "ComfyUI" / "input"
INPUT_IMAGE = INPUT_DIR / "flux2_test_mug.png"
MASK_IMAGE = INPUT_DIR / "flux2_test_mug_mask.png"


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(f"Expected generated test image not found: {SOURCE}")
    INPUT_DIR.mkdir(exist_ok=True)
    shutil.copy2(SOURCE, INPUT_IMAGE)

    with Image.open(SOURCE) as original:
        width, height = original.size

    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    # The generated mug is centered. This deliberately leaves a wide untouched
    # border, suitable for verifying final pixel-preserving compositing.
    draw.rounded_rectangle((90, 90, 395, 410), radius=55, fill=255)
    draw.ellipse((320, 145, 455, 355), fill=255)
    mask.save(MASK_IMAGE)

    print(json.dumps({"input": str(INPUT_IMAGE), "mask": str(MASK_IMAGE), "size": [width, height]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
