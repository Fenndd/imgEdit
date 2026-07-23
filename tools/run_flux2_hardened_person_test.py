"""Run quantized 720p person edits with full-frame multi-reference identity preservation.

Every scenario starts from a byte-for-byte copy of the original photo as its
first reference. Additional face/hair, closer facial-identity, and upper-body
crops reinforce the likeness; the body case adds an outpaint-layout cue.
Every result is a clean, full-frame identity-preserving generation: no source
pixels are composited back, so face size, camera distance, pose, and
expression may change naturally.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
import urllib.error
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_flux2_t2i_test import ROOT, gpu_memory_mib, ram_used_mib, request_json


DEFAULT_MODEL = "flux-2-klein-base-4b-Q4_K_M.gguf"
WIDTH = 1280
HEIGHT = 720
INPUT_DIR = ROOT / "ComfyUI" / "input"
BASE_WIDTH = 304
BASE_HEIGHT = 536
PAD_LEFT = 488
PAD_TOP = 0
PAD_RIGHT = 488
PAD_BOTTOM = 184
PAD_FEATHERING = 32
IDENTITY_ANCHOR = (
    "The identity reference is binding: preserve the same individual, with long dark-brown centre-parted hair, "
    "defined dark eyebrows, dark almond-shaped eyes, the same natural skin texture, facial proportions, eye shape, "
    "nose and overall facial structure. Do not substitute a lookalike or a different person. "
)

SCENARIOS = {
    "body": {
        "prefix": "FLUX2_Q4_HARDENED_BODY_720P",
        "layout_reference": "outpaint",
        "instruction": (
            "Use case: identity-preserve, full-body outpainting. Create a realistic landscape full-body photograph of the exact same "
            "person, seated naturally on a wooden chair. Complete the missing lower body and legs so both feet are visible on the floor. "
            "Only slight natural body adjustments are allowed. Preserve the same face, facial proportions, age, skin texture, hair color, "
            "hairstyle, white dress, sash, head position and indoor classroom setting. "
            + IDENTITY_ANCHOR + "No text, no watermark."
        ),
    },
    "emotion": {
        "prefix": "FLUX2_Q4_HARDENED_EMOTION_720P",
        "layout_reference": "original",
        "instruction": (
            "Use case: identity-preserve facial expression edit. Keep the exact same person, head position, hairstyle, clothing, body, "
            "camera framing and background. Change only the expression to a subtle warm, closed-mouth smile. Preserve the person's exact "
            "facial identity, proportions, age and skin texture. " + IDENTITY_ANCHOR + "No text, no watermark."
        ),
    },
    "head_turn": {
        "prefix": "FLUX2_Q4_HARDENED_HEADTURN_720P",
        "layout_reference": "original",
        "instruction": (
            "Use case: identity-preserve mild head-turn edit. Keep the exact same person, age, facial identity, facial proportions, "
            "skin texture, hair color, hairstyle, white dress, sash, body and camera framing. Turn her head only about 15 degrees to her left, "
            "with eyes still toward the camera. Keep the change subtle and natural. " + IDENTITY_ANCHOR + "No text, no watermark."
        ),
    },
    "distance": {
        "prefix": "FLUX2_Q4_HARDENED_DISTANCE_720P",
        "layout_reference": "original",
        "instruction": (
            "Use case: identity-preserve spatial reframe. Create a realistic landscape medium portrait of the exact same person in the same "
            "indoor classroom. The camera is moderately closer, so her face and upper body naturally occupy more of the frame. Preserve her "
            "facial identity, proportions, age, skin texture, hair color, hairstyle, white dress and sash; only the camera distance and framing "
            "change. " + IDENTITY_ANCHOR + "No text, no watermark."
        ),
    },
}


def save_rgb(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(path, "PNG")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quant_label(model_name: str) -> str:
    return "Q5" if "Q5" in model_name else "Q4"


def prepare_references(source: Path) -> dict[str, str]:
    """Make crop references in the actual outpaint coordinate space.

    A byte-for-byte copy of the user image is the first reference in every
    prompt.  Crops are supplemental identity cues only.  The padded layout
    is used only for the body-outpaint scenario and is never a blurred scene.
    """
    with Image.open(source) as original:
        source_rgb = original.convert("RGB")
        composition = ImageOps.fit(source_rgb, (BASE_WIDTH, BASE_HEIGHT), Image.Resampling.LANCZOS, centering=(0.5, 0.5))

        width, height = source_rgb.size
        face_crop = source_rgb.crop((int(width * 0.12), int(height * 0.06), int(width * 0.88), int(height * 0.52)))
        face_crop = ImageOps.fit(face_crop, (640, 640), Image.Resampling.LANCZOS, centering=(0.5, 0.35))
        identity_crop = source_rgb.crop((int(width * 0.19), int(height * 0.07), int(width * 0.81), int(height * 0.50)))
        identity_crop = ImageOps.fit(identity_crop, (640, 640), Image.Resampling.LANCZOS, centering=(0.5, 0.35))
        upper_crop = source_rgb.crop((int(width * 0.04), int(height * 0.03), int(width * 0.96), int(height * 0.72)))
        upper_crop = ImageOps.fit(upper_crop, (640, 640), Image.Resampling.LANCZOS, centering=(0.5, 0.38))

    paths = {
        "original": INPUT_DIR / f"q4_identity_original_reference{source.suffix.lower()}",
        "composition": INPUT_DIR / "q4_identity_outpaint_source_304x536.png",
        "face": INPUT_DIR / "q4_identity_face_hair_ref.png",
        "identity": INPUT_DIR / "q4_identity_close_face_ref.png",
        "upper": INPUT_DIR / "q4_identity_upper_body_ref.png",
    }
    if source.resolve() != paths["original"].resolve():
        shutil.copy2(source, paths["original"])
    save_rgb(composition, paths["composition"])
    save_rgb(face_crop, paths["face"])
    save_rgb(identity_crop, paths["identity"])
    save_rgb(upper_crop, paths["upper"])

    return {name: path.name for name, path in paths.items()}


def make_prompt(refs: dict[str, str], scenario: dict[str, Any], seed: int, steps: int, model_name: str) -> dict[str, Any]:
    """Return an original-first, multi-reference full-generation graph."""
    use_outpaint_layout = scenario["layout_reference"] == "outpaint"
    filename_prefix = scenario["prefix"].replace("Q4", quant_label(model_name))
    nodes: dict[str, Any] = {
        "1": {"class_type": "LoadImage", "inputs": {"image": refs["original"]}},
        "2": {"class_type": "LoadImage", "inputs": {"image": refs["face"]}},
        "3": {"class_type": "LoadImage", "inputs": {"image": refs["upper"]}},
        "40": {"class_type": "LoadImage", "inputs": {"image": refs["identity"]}},
        "39": {"class_type": "LoadImage", "inputs": {"image": refs["composition"]}},
        "38": {"class_type": "ImagePadForOutpaint", "inputs": {"image": ["39", 0], "left": PAD_LEFT, "top": PAD_TOP, "right": PAD_RIGHT, "bottom": PAD_BOTTOM, "feathering": PAD_FEATHERING}},
        "4": {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": ["1", 0], "upscale_method": "lanczos", "megapixels": 0.50, "resolution_steps": 16}},
        "5": {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": ["2", 0], "upscale_method": "lanczos", "megapixels": 0.40, "resolution_steps": 16}},
        "6": {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": ["3", 0], "upscale_method": "lanczos", "megapixels": 0.30, "resolution_steps": 16}},
        "41": {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": ["40", 0], "upscale_method": "lanczos", "megapixels": 0.40, "resolution_steps": 16}},
        "45": {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": ["38", 0], "upscale_method": "lanczos", "megapixels": 0.30, "resolution_steps": 16}},
        "7": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": model_name}},
        "8": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "flux2", "device": "cpu"}},
        "9": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
        "10": {"class_type": "CLIPTextEncode", "inputs": {"text": scenario["instruction"], "clip": ["8", 0]}},
        "11": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["8", 0]}},
        "12": {"class_type": "VAEEncode", "inputs": {"pixels": ["4", 0], "vae": ["9", 0]}},
        "13": {"class_type": "VAEEncode", "inputs": {"pixels": ["5", 0], "vae": ["9", 0]}},
        "14": {"class_type": "VAEEncode", "inputs": {"pixels": ["6", 0], "vae": ["9", 0]}},
        "42": {"class_type": "VAEEncode", "inputs": {"pixels": ["41", 0], "vae": ["9", 0]}},
        "46": {"class_type": "VAEEncode", "inputs": {"pixels": ["45", 0], "vae": ["9", 0]}},
        "22": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "23": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "24": {"class_type": "Flux2Scheduler", "inputs": {"steps": steps, "width": WIDTH, "height": HEIGHT}},
        "25": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": WIDTH, "height": HEIGHT, "batch_size": 1}},
        "26": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["22", 0], "guider": ["21", 0], "sampler": ["23", 0], "sigmas": ["24", 0], "latent_image": ["25", 0]}},
        "27": {"class_type": "VAEDecode", "inputs": {"samples": ["26", 0], "vae": ["9", 0]}},
        "37": {"class_type": "SaveImage", "inputs": {"images": ["27", 0], "filename_prefix": filename_prefix}},
    }
    latent_ids = ["12", "13", "14", "42"]
    if use_outpaint_layout:
        latent_ids.insert(1, "46")
    positive: list[Any] = ["10", 0]
    negative: list[Any] = ["11", 0]
    for index, latent_id in enumerate(latent_ids):
        positive_id = str(100 + index)
        negative_id = str(110 + index)
        nodes[positive_id] = {"class_type": "ReferenceLatent", "inputs": {"conditioning": positive, "latent": [latent_id, 0]}}
        nodes[negative_id] = {"class_type": "ReferenceLatent", "inputs": {"conditioning": negative, "latent": [latent_id, 0]}}
        positive = [positive_id, 0]
        negative = [negative_id, 0]
    nodes["21"] = {"class_type": "CFGGuider", "inputs": {"model": ["7", 0], "positive": positive, "negative": negative, "cfg": 5.0}}
    return {"prompt": nodes}


def run_scenario(refs: dict[str, str], name: str, scenario: dict[str, Any], seed: int, steps: int, timeout: int, model_name: str, result: dict[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    run: dict[str, Any] = {
        "name": name,
        "instruction": scenario["instruction"],
        "seed": seed,
        "model_name": model_name,
        "face_composite_policy": "original_primary_plus_crops__full_generation__face_scale_free",
        "layout_reference": scenario["layout_reference"],
    }
    payload = make_prompt(refs, scenario, seed, steps, model_name)
    prompt_id = request_json("/prompt", payload)["prompt_id"]
    run["prompt_id"] = prompt_id
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        gpu_used, _ = gpu_memory_mib()
        ram_used = ram_used_mib()
        if gpu_used is not None:
            result["peak_gpu_mib"] = max(result["peak_gpu_mib"] or 0, gpu_used)
        if ram_used is not None:
            result["peak_ram_mib"] = max(result["peak_ram_mib"] or 0, ram_used)
        history = request_json(f"/history/{prompt_id}")
        if prompt_id in history:
            entry = history[prompt_id]
            run["status"] = entry.get("status", {})
            run["outputs"] = entry.get("outputs", {})
            images = run["outputs"].get("37", {}).get("images", [])
            if run["status"].get("status_str") != "success" or not images:
                raise RuntimeError(f"{name} failed: {run['status']}")
            run["output"] = images[0]["filename"]
            run["elapsed_seconds"] = round(time.monotonic() - started, 2)
            return run
        time.sleep(1)
    raise TimeoutError(f"{name} timed out after {timeout} seconds")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--mode", choices=("all", *SCENARIOS), default="all")
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--seed", type=int, default=123456789)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    model_quantization = quant_label(args.model)

    started = time.time()
    result: dict[str, Any] = {
        "kind": f"FLUX.2 Klein {model_quantization} hardened multi-reference person edit test",
        "model_name": args.model,
        "resolution": f"{WIDTH}x{HEIGHT}",
        "steps": args.steps,
        "source": str(args.source),
        "references": {"original": "verbatim source PNG, always first and primary reference", "composition": "outpaint layout cue for the body scenario only", "face": "face and hair crop", "identity": "closer facial-identity crop", "upper": "upper-body and clothing crop"},
        "face_policy": "original-first plus crop references for every scenario; no pixel-lock or source compositing",
        "outpaint": {"base_size": f"{BASE_WIDTH}x{BASE_HEIGHT}", "padding": {"left": PAD_LEFT, "top": PAD_TOP, "right": PAD_RIGHT, "bottom": PAD_BOTTOM, "feathering": PAD_FEATHERING}},
        "baseline_gpu_mib": gpu_memory_mib()[0],
        "baseline_ram_mib": ram_used_mib(),
        "peak_gpu_mib": None,
        "peak_ram_mib": None,
        "runs": [],
        "started_at_unix": started,
    }
    result["peak_gpu_mib"] = result["baseline_gpu_mib"]
    result["peak_ram_mib"] = result["baseline_ram_mib"]
    try:
        if not args.source.is_file():
            raise FileNotFoundError(args.source)
        refs = prepare_references(args.source)
        result["reference_files"] = refs
        original_copy = INPUT_DIR / refs["original"]
        result["original_reference_verification"] = {
            "source_sha256": sha256(args.source),
            "input_copy": str(original_copy),
            "input_copy_sha256": sha256(original_copy),
        }
        result["original_reference_verification"]["byte_identical"] = (
            result["original_reference_verification"]["source_sha256"]
            == result["original_reference_verification"]["input_copy_sha256"]
        )
        if not result["original_reference_verification"]["byte_identical"]:
            raise RuntimeError("The primary reference copy differs from the user source")
        names = list(SCENARIOS) if args.mode == "all" else [args.mode]
        for offset, name in enumerate(names):
            result["runs"].append(run_scenario(refs, name, SCENARIOS[name], args.seed + offset, args.steps, args.timeout, args.model, result))
        result["completed"] = True
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError, FileNotFoundError, RuntimeError, TimeoutError) as error:
        result["completed"] = False
        result["error"] = f"{type(error).__name__}: {error}"

    result["elapsed_seconds"] = round(time.time() - started, 2)
    results_dir = ROOT / "test_results"
    results_dir.mkdir(exist_ok=True)
    result_path = results_dir / f"hardened_person_{model_quantization.lower()}_720p_{int(started)}.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result_path": str(result_path), **result}, ensure_ascii=False, indent=2))
    return 0 if result.get("completed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
