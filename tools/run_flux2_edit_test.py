"""Queue local single-image and masked FLUX.2 Klein Base GGUF edit tests."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
from pathlib import Path
from typing import Any

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_flux2_t2i_test import ROOT, gpu_memory_mib, ram_used_mib, request_json


WORKFLOW_DIR = ROOT / "ComfyUI" / "user" / "default" / "workflows" / "FLUX2_KLEIN_4B"


def base_nodes(steps: int, seed: int, instruction: str) -> dict[str, Any]:
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": "flux2_test_mug.png"}},
        "2": {
            "class_type": "ImageScaleToTotalPixels",
            "inputs": {"image": ["1", 0], "upscale_method": "lanczos", "megapixels": 0.25, "resolution_steps": 16},
        },
        "3": {"class_type": "GetImageSize", "inputs": {"image": ["2", 0]}},
        "4": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "flux-2-klein-base-4b-Q4_K_M.gguf"}},
        "5": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "flux2", "device": "cpu"}},
        "6": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": instruction, "clip": ["5", 0]}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["5", 0]}},
        "9": {"class_type": "VAEEncode", "inputs": {"pixels": ["2", 0], "vae": ["6", 0]}},
        "10": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["7", 0], "latent": ["9", 0]}},
        "11": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["8", 0], "latent": ["9", 0]}},
        "12": {"class_type": "CFGGuider", "inputs": {"model": ["4", 0], "positive": ["10", 0], "negative": ["11", 0], "cfg": 5.0}},
        "13": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "14": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "15": {"class_type": "Flux2Scheduler", "inputs": {"steps": steps, "width": ["3", 0], "height": ["3", 1]}},
        "16": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": ["3", 0], "height": ["3", 1], "batch_size": 1}},
        "17": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {"noise": ["13", 0], "guider": ["12", 0], "sampler": ["14", 0], "sigmas": ["15", 0], "latent_image": ["16", 0]},
        },
        "18": {"class_type": "VAEDecode", "inputs": {"samples": ["17", 0], "vae": ["6", 0]}},
    }


def add_mask_nodes(nodes: dict[str, Any], prefix: str) -> None:
    nodes.update(
        {
            "20": {"class_type": "LoadImageMask", "inputs": {"image": "flux2_test_mug_mask.png", "channel": "red"}},
            "21": {"class_type": "MaskToImage", "inputs": {"mask": ["20", 0]}},
            "22": {
                "class_type": "ImageScaleToTotalPixels",
                "inputs": {"image": ["21", 0], "upscale_method": "nearest-exact", "megapixels": 0.25, "resolution_steps": 16},
            },
            "23": {"class_type": "ImageToMask", "inputs": {"image": ["22", 0], "channel": "red"}},
            "24": {"class_type": "GrowMask", "inputs": {"mask": ["23", 0], "expand": 16, "tapered_corners": True}},
            "25": {"class_type": "MaskToImage", "inputs": {"mask": ["24", 0]}},
            "26": {"class_type": "ImageBlur", "inputs": {"image": ["25", 0], "blur_radius": 8, "sigma": 4.0}},
            "27": {"class_type": "ImageToMask", "inputs": {"image": ["26", 0], "channel": "red"}},
            "28": {
                "class_type": "ImageCompositeMasked",
                "inputs": {"destination": ["2", 0], "source": ["18", 0], "x": 0, "y": 0, "resize_source": False, "mask": ["27", 0]},
            },
            "29": {"class_type": "SaveImage", "inputs": {"images": ["28", 0], "filename_prefix": prefix}},
        }
    )


def verify_protected_border(output_path: Path) -> dict[str, Any]:
    """Check pixels far outside the edited mask are bit-for-bit original."""
    import numpy as np
    from scipy.ndimage import binary_erosion

    source_path = ROOT / "ComfyUI" / "input" / "flux2_test_mug.png"
    mask_path = ROOT / "ComfyUI" / "input" / "flux2_test_mug_mask.png"
    source = np.asarray(Image.open(source_path).convert("RGB"))
    output = np.asarray(Image.open(output_path).convert("RGB"))
    mask = np.asarray(Image.open(mask_path).convert("L")) > 0
    safe = binary_erosion(~mask, iterations=36)
    mismatch = np.any(source != output, axis=2) & safe
    return {"safe_pixel_count": int(safe.sum()), "mismatched_safe_pixels": int(mismatch.sum()), "exact_outside_mask": bool(not mismatch.any())}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("single", "masked"), required=True)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--seed", type=int, default=123456789)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()

    prefix = "FLUX2_KLEIN_MASKED_EDIT_TEST" if args.mode == "masked" else "FLUX2_KLEIN_SINGLE_EDIT_TEST"
    instruction = "Change only the color of the mug from red to dark blue. Preserve its exact shape, position, lighting, table and background."
    nodes = base_nodes(args.steps, args.seed, instruction)
    if args.mode == "masked":
        add_mask_nodes(nodes, prefix)
        workflow_path = WORKFLOW_DIR / "04_MASKED_LOCAL_EDIT.json"
        output_node = "29"
    else:
        nodes["19"] = {"class_type": "SaveImage", "inputs": {"images": ["18", 0], "filename_prefix": prefix}}
        workflow_path = WORKFLOW_DIR / "02_SINGLE_IMAGE_EDIT.json"
        output_node = "19"

    result: dict[str, Any] = {
        "kind": f"FLUX.2 Klein Base GGUF {args.mode} image edit",
        "steps": args.steps,
        "seed": args.seed,
        "resolution": "512x512",
        "instruction": instruction,
        "launcher_profile": "balanced-equivalent, CLIP offloaded to CPU",
        "baseline_gpu_mib": gpu_memory_mib()[0],
        "baseline_ram_mib": ram_used_mib(),
        "peak_gpu_mib": None,
        "peak_ram_mib": None,
        "started_at_unix": time.time(),
    }
    result["peak_gpu_mib"] = result["baseline_gpu_mib"]
    result["peak_ram_mib"] = result["baseline_ram_mib"]

    try:
        payload: dict[str, Any] = {"prompt": nodes}
        payload["extra_data"] = {"extra_pnginfo": {"workflow": json.loads(workflow_path.read_text(encoding="utf-8"))}}
        result["workflow_metadata_source"] = str(workflow_path)
        prompt_id = request_json("/prompt", payload)["prompt_id"]
        result["prompt_id"] = prompt_id
        deadline = time.monotonic() + args.timeout
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
                result["status"] = entry.get("status", {})
                result["outputs"] = entry.get("outputs", {})
                result["completed"] = True
                images = result["outputs"].get(output_node, {}).get("images", [])
                if args.mode == "masked" and images:
                    result["outside_mask_verification"] = verify_protected_border(ROOT / "ComfyUI" / "output" / images[0]["filename"])
                break
            time.sleep(1)
        else:
            result["completed"] = False
            result["error"] = f"Timed out after {args.timeout} seconds"
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError, FileNotFoundError) as error:
        result["completed"] = False
        result["error"] = f"{type(error).__name__}: {error}"

    result["elapsed_seconds"] = round(time.time() - result["started_at_unix"], 2)
    results_dir = ROOT / "test_results"
    results_dir.mkdir(exist_ok=True)
    path = results_dir / f"{args.mode}_edit_steps_{args.steps}_{int(result['started_at_unix'])}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result_path": str(path), **result}, ensure_ascii=False, indent=2))
    return 0 if result.get("completed") and result.get("status", {}).get("status_str") == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())
