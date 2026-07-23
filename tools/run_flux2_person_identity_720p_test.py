"""Run two chained local Q4 portrait edits to probe identity preservation at 720p.

The first pass changes only the environment.  The second pass uses that output
as its input and requests a new pose, exposing identity drift across edits.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import urllib.error
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_flux2_t2i_test import ROOT, gpu_memory_mib, ram_used_mib, request_json


MODEL = "flux-2-klein-base-4b-Q4_K_M.gguf"
WIDTH = 1280
HEIGHT = 720
WORKFLOW = ROOT / "ComfyUI" / "user" / "default" / "workflows" / "FLUX2_KLEIN_4B" / "05_IDENTITY_PRESERVATION.json"
INPUT_DIR = ROOT / "ComfyUI" / "input"
OUTPUT_DIR = ROOT / "ComfyUI" / "output"


def prepare_input(source: Path, target_name: str) -> Path:
    """Fit the portrait into a 16:9 720p canvas with a non-destructive backdrop."""
    target = INPUT_DIR / target_name
    with Image.open(source) as image:
        source_rgb = image.convert("RGB")
        background = source_rgb.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(radius=18))
        foreground = source_rgb.copy()
        foreground.thumbnail((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        offset = ((WIDTH - foreground.width) // 2, (HEIGHT - foreground.height) // 2)
        background.paste(foreground, offset)
        background.save(target, "PNG")
    return target


def make_prompt(
    image_name: str,
    instruction: str,
    prefix: str,
    seed: int,
    steps: int,
) -> dict[str, Any]:
    return {
        "prompt": {
            "1": {"class_type": "LoadImage", "inputs": {"image": image_name}},
            "2": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": MODEL}},
            "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "flux2", "device": "cpu"}},
            "4": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
            "5": {"class_type": "CLIPTextEncode", "inputs": {"text": instruction, "clip": ["3", 0]}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["3", 0]}},
            "7": {"class_type": "VAEEncode", "inputs": {"pixels": ["1", 0], "vae": ["4", 0]}},
            "8": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["5", 0], "latent": ["7", 0]}},
            "9": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["6", 0], "latent": ["7", 0]}},
            "10": {"class_type": "CFGGuider", "inputs": {"model": ["2", 0], "positive": ["8", 0], "negative": ["9", 0], "cfg": 5.0}},
            "11": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
            "12": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
            "13": {"class_type": "Flux2Scheduler", "inputs": {"steps": steps, "width": WIDTH, "height": HEIGHT}},
            "14": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": WIDTH, "height": HEIGHT, "batch_size": 1}},
            "15": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["11", 0], "guider": ["10", 0], "sampler": ["12", 0], "sigmas": ["13", 0], "latent_image": ["14", 0]}},
            "16": {"class_type": "VAEDecode", "inputs": {"samples": ["15", 0], "vae": ["4", 0]}},
            "17": {"class_type": "SaveImage", "inputs": {"images": ["16", 0], "filename_prefix": prefix}},
        }
    }


def queue_and_wait(payload: dict[str, Any], result: dict[str, Any], timeout: int) -> str:
    prompt_id = request_json("/prompt", payload)["prompt_id"]
    result["prompt_id"] = prompt_id
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
            result["status"] = entry.get("status", {})
            result["outputs"] = entry.get("outputs", {})
            images = result["outputs"].get("17", {}).get("images", [])
            if entry.get("status", {}).get("status_str") != "success" or not images:
                raise RuntimeError(f"Generation failed: {entry.get('status', {})}")
            return images[0]["filename"]
        time.sleep(1)
    raise TimeoutError(f"Timed out after {timeout} seconds")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--seed", type=int, default=123456789)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()

    started = time.time()
    result: dict[str, Any] = {
        "kind": "FLUX.2 Klein Q4 chained identity-preservation portrait test",
        "model_name": MODEL,
        "resolution": f"{WIDTH}x{HEIGHT}",
        "steps": args.steps,
        "seed": args.seed,
        "source": str(args.source),
        "workflow_metadata_source": str(WORKFLOW),
        "baseline_gpu_mib": gpu_memory_mib()[0],
        "baseline_ram_mib": ram_used_mib(),
        "peak_gpu_mib": None,
        "peak_ram_mib": None,
        "passes": [],
        "started_at_unix": started,
    }
    result["peak_gpu_mib"] = result["baseline_gpu_mib"]
    result["peak_ram_mib"] = result["baseline_ram_mib"]

    try:
        if not args.source.is_file():
            raise FileNotFoundError(args.source)
        original_name = "person_identity_720p_original.png"
        prepare_input(args.source, original_name)

        background_instruction = (
            "Use case: identity-preserve. Replace only the indoor background with a softly sunlit Venetian garden courtyard, "
            "warm stone walls and greenery. Keep the exact same woman: identical face, facial proportions, skin texture, "
            "age, hair, white dress, sash, hands, seated pose, framing and camera angle. Do not alter the person. "
            "No text, no watermark."
        )
        first = {"name": "background_only", "instruction": background_instruction, "peak_gpu_mib": result["peak_gpu_mib"], "peak_ram_mib": result["peak_ram_mib"]}
        first_payload = make_prompt(original_name, background_instruction, "FLUX2_Q4_PERSON_720P_BACKGROUND", args.seed, args.steps)
        first_payload["extra_data"] = {"extra_pnginfo": {"workflow": json.loads(WORKFLOW.read_text(encoding="utf-8"))}}
        first_output = queue_and_wait(first_payload, result, args.timeout)
        first["output"] = first_output
        result["passes"].append(first)

        chained_name = "person_identity_720p_background_pass.png"
        shutil.copy2(OUTPUT_DIR / first_output, INPUT_DIR / chained_name)
        pose_instruction = (
            "Use case: identity-preserve. The exact same woman is now standing in the same Venetian garden courtyard, "
            "turned about 30 degrees to her left while looking directly at the camera, with relaxed hands at her waist. "
            "Preserve the exact face, facial proportions, skin texture, age, hair, hair color, body proportions, white dress and sash. "
            "Only change the pose and spatial placement; do not turn her into a different person. No text, no watermark."
        )
        second = {"name": "pose_change_from_previous_output", "instruction": pose_instruction, "input": first_output, "peak_gpu_mib": result["peak_gpu_mib"], "peak_ram_mib": result["peak_ram_mib"]}
        second_payload = make_prompt(chained_name, pose_instruction, "FLUX2_Q4_PERSON_720P_POSE", args.seed + 1, args.steps)
        second_payload["extra_data"] = {"extra_pnginfo": {"workflow": json.loads(WORKFLOW.read_text(encoding="utf-8"))}}
        second_output = queue_and_wait(second_payload, result, args.timeout)
        second["output"] = second_output
        result["passes"].append(second)
        result["completed"] = True
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError, FileNotFoundError, RuntimeError, TimeoutError) as error:
        result["completed"] = False
        result["error"] = f"{type(error).__name__}: {error}"

    result["elapsed_seconds"] = round(time.time() - started, 2)
    results_dir = ROOT / "test_results"
    results_dir.mkdir(exist_ok=True)
    result_path = results_dir / f"person_identity_720p_q4_{int(started)}.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result_path": str(result_path), **result}, ensure_ascii=False, indent=2))
    return 0 if result.get("completed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
