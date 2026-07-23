"""Run a local three-reference + mask FLUX.2 Klein identity-preservation test."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_flux2_edit_test import verify_protected_border
from run_flux2_t2i_test import ROOT, gpu_memory_mib, ram_used_mib, request_json


WORKFLOW = ROOT / "ComfyUI" / "user" / "default" / "workflows" / "FLUX2_KLEIN_4B" / "05_IDENTITY_PRESERVATION.json"


def make_prompt(steps: int, seed: int) -> dict[str, Any]:
    instruction = "Change only the color of the mug from red to dark blue. Preserve the exact subject identity, shape, composition, lighting, table and pixels outside the mask."
    return {
        "prompt": {
            "1": {"class_type": "LoadImage", "inputs": {"image": "flux2_test_mug.png"}},
            "2": {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": ["1", 0], "upscale_method": "lanczos", "megapixels": 0.25, "resolution_steps": 16}},
            "3": {"class_type": "LoadImage", "inputs": {"image": "flux2_test_mug.png"}},
            "4": {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": ["3", 0], "upscale_method": "lanczos", "megapixels": 0.25, "resolution_steps": 16}},
            "5": {"class_type": "LoadImage", "inputs": {"image": "flux2_test_mug.png"}},
            "6": {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": ["5", 0], "upscale_method": "lanczos", "megapixels": 0.25, "resolution_steps": 16}},
            "7": {"class_type": "GetImageSize", "inputs": {"image": ["2", 0]}},
            "8": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "flux-2-klein-base-4b-Q4_K_M.gguf"}},
            "9": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "flux2", "device": "cpu"}},
            "10": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
            "11": {"class_type": "CLIPTextEncode", "inputs": {"text": instruction, "clip": ["9", 0]}},
            "12": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["9", 0]}},
            "13": {"class_type": "VAEEncode", "inputs": {"pixels": ["2", 0], "vae": ["10", 0]}},
            "14": {"class_type": "VAEEncode", "inputs": {"pixels": ["4", 0], "vae": ["10", 0]}},
            "15": {"class_type": "VAEEncode", "inputs": {"pixels": ["6", 0], "vae": ["10", 0]}},
            "16": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["11", 0], "latent": ["13", 0]}},
            "17": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["12", 0], "latent": ["13", 0]}},
            "18": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["16", 0], "latent": ["14", 0]}},
            "19": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["17", 0], "latent": ["14", 0]}},
            "20": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["18", 0], "latent": ["15", 0]}},
            "21": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["19", 0], "latent": ["15", 0]}},
            "22": {"class_type": "CFGGuider", "inputs": {"model": ["8", 0], "positive": ["20", 0], "negative": ["21", 0], "cfg": 5.0}},
            "23": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
            "24": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
            "25": {"class_type": "Flux2Scheduler", "inputs": {"steps": steps, "width": ["7", 0], "height": ["7", 1]}},
            "26": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": ["7", 0], "height": ["7", 1], "batch_size": 1}},
            "27": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["23", 0], "guider": ["22", 0], "sampler": ["24", 0], "sigmas": ["25", 0], "latent_image": ["26", 0]}},
            "28": {"class_type": "VAEDecode", "inputs": {"samples": ["27", 0], "vae": ["10", 0]}},
            "30": {"class_type": "LoadImageMask", "inputs": {"image": "flux2_test_mug_mask.png", "channel": "red"}},
            "31": {"class_type": "MaskToImage", "inputs": {"mask": ["30", 0]}},
            "32": {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": ["31", 0], "upscale_method": "nearest-exact", "megapixels": 0.25, "resolution_steps": 16}},
            "33": {"class_type": "ImageToMask", "inputs": {"image": ["32", 0], "channel": "red"}},
            "34": {"class_type": "GrowMask", "inputs": {"mask": ["33", 0], "expand": 16, "tapered_corners": True}},
            "35": {"class_type": "MaskToImage", "inputs": {"mask": ["34", 0]}},
            "36": {"class_type": "ImageBlur", "inputs": {"image": ["35", 0], "blur_radius": 8, "sigma": 4.0}},
            "37": {"class_type": "ImageToMask", "inputs": {"image": ["36", 0], "channel": "red"}},
            "38": {"class_type": "ImageCompositeMasked", "inputs": {"destination": ["2", 0], "source": ["28", 0], "x": 0, "y": 0, "resize_source": False, "mask": ["37", 0]}},
            "39": {"class_type": "SaveImage", "inputs": {"images": ["38", 0], "filename_prefix": "FLUX2_KLEIN_IDENTITY_TEST"}},
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--seed", type=int, default=123456789)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    started = time.time()
    result: dict[str, Any] = {
        "kind": "FLUX.2 Klein Base GGUF three-reference identity + masked local edit",
        "steps": args.steps,
        "seed": args.seed,
        "resolution": "512x512",
        "reference_count": 3,
        "baseline_gpu_mib": gpu_memory_mib()[0],
        "baseline_ram_mib": ram_used_mib(),
        "peak_gpu_mib": None,
        "peak_ram_mib": None,
        "workflow_metadata_source": str(WORKFLOW),
        "started_at_unix": started,
    }
    result["peak_gpu_mib"] = result["baseline_gpu_mib"]
    result["peak_ram_mib"] = result["baseline_ram_mib"]
    try:
        payload = make_prompt(args.steps, args.seed)
        payload["extra_data"] = {"extra_pnginfo": {"workflow": json.loads(WORKFLOW.read_text(encoding="utf-8"))}}
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
                images = result["outputs"].get("39", {}).get("images", [])
                if images:
                    result["outside_mask_verification"] = verify_protected_border(ROOT / "ComfyUI" / "output" / images[0]["filename"])
                break
            time.sleep(1)
        else:
            result["completed"] = False
            result["error"] = f"Timed out after {args.timeout} seconds"
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError, FileNotFoundError) as error:
        result["completed"] = False
        result["error"] = f"{type(error).__name__}: {error}"
    result["elapsed_seconds"] = round(time.time() - started, 2)
    results_dir = ROOT / "test_results"
    results_dir.mkdir(exist_ok=True)
    path = results_dir / f"identity_steps_{args.steps}_{int(started)}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result_path": str(path), **result}, ensure_ascii=False, indent=2))
    return 0 if result.get("completed") and result.get("status", {}).get("status_str") == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())
