"""Queue a local FLUX.2 Klein GGUF text-to-image test and collect peak memory.

This helper uses only the local ComfyUI HTTP endpoint.  It never contacts an
external service and is intended to be run with this installation's embedded
Python after ComfyUI has started.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SERVER = "http://127.0.0.1:8188"


def request_json(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers: dict[str, str] = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{SERVER}{path}", data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def gpu_memory_mib() -> tuple[int | None, int | None]:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        used, total = result.stdout.strip().splitlines()[0].split(",")
        return int(used.strip()), int(total.strip())
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None, None


def ram_used_mib() -> int | None:
    try:
        import psutil

        return round(psutil.virtual_memory().used / 1024 / 1024)
    except Exception:
        return None


def make_prompt(
    steps: int,
    seed: int,
    filename_prefix: str,
    model_name: str,
    width: int,
    height: int,
) -> dict[str, Any]:
    return {
        "prompt": {
            "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": model_name}},
            "2": {
                "class_type": "CLIPLoader",
                "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "flux2", "device": "cpu"},
            },
            "3": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "A realistic studio photograph of a centered red ceramic mug on a wooden table, soft window lighting, detailed texture.",
                    "clip": ["2", 0],
                },
            },
            "5": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["2", 0]}},
            "6": {
                "class_type": "CFGGuider",
                "inputs": {"model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0], "cfg": 5.0},
            },
            "7": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
            "8": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
            "9": {"class_type": "Flux2Scheduler", "inputs": {"steps": steps, "width": width, "height": height}},
            "10": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
            "11": {
                "class_type": "SamplerCustomAdvanced",
                "inputs": {
                    "noise": ["7", 0],
                    "guider": ["6", 0],
                    "sampler": ["8", 0],
                    "sigmas": ["9", 0],
                    "latent_image": ["10", 0],
                },
            },
            "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["3", 0]}},
            "13": {"class_type": "SaveImage", "inputs": {"images": ["12", 0], "filename_prefix": filename_prefix}},
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=1)
    parser.add_argument("--seed", type=int, default=123456789)
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--prefix", default="FLUX2_KLEIN_GGUF_TEST")
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--height", type=int, default=512)
    parser.add_argument(
        "--model",
        default="flux-2-klein-base-4b-Q4_K_M.gguf",
        help="Installed GGUF filename from ComfyUI/models/diffusion_models.",
    )
    parser.add_argument(
        "--workflow-metadata",
        default=str(ROOT / "ComfyUI" / "user" / "default" / "workflows" / "FLUX2_KLEIN_4B" / "01_TEXT_TO_IMAGE_MAX_QUALITY.json"),
        help="UI workflow JSON to embed in the output PNG",
    )
    args = parser.parse_args()
    if args.width <= 0 or args.height <= 0 or args.width % 16 or args.height % 16:
        parser.error("--width and --height must be positive multiples of 16")

    baseline_gpu, gpu_total = gpu_memory_mib()
    baseline_ram = ram_used_mib()
    started = time.time()
    result: dict[str, Any] = {
        "kind": "FLUX.2 Klein Base GGUF local text-to-image",
        "model_name": args.model,
        "steps": args.steps,
        "seed": args.seed,
        "resolution": f"{args.width}x{args.height}",
        "launcher_profile": "balanced-equivalent, CLIP offloaded to CPU",
        "started_at_unix": started,
        "baseline_gpu_mib": baseline_gpu,
        "gpu_total_mib": gpu_total,
        "baseline_ram_mib": baseline_ram,
        "peak_gpu_mib": baseline_gpu,
        "peak_ram_mib": baseline_ram,
    }

    try:
        payload: dict[str, Any] = make_prompt(
            args.steps,
            args.seed,
            args.prefix,
            args.model,
            args.width,
            args.height,
        )
        metadata_path = Path(args.workflow_metadata)
        if metadata_path.is_file():
            payload["extra_data"] = {"extra_pnginfo": {"workflow": json.loads(metadata_path.read_text(encoding="utf-8"))}}
            result["workflow_metadata_source"] = str(metadata_path)
        else:
            result["workflow_metadata_source"] = None
            result["workflow_metadata_warning"] = f"Workflow metadata file not found: {metadata_path}"
        queued = request_json("/prompt", payload)
        prompt_id = queued["prompt_id"]
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
                break
            time.sleep(1)
        else:
            result["completed"] = False
            result["error"] = f"Timed out after {args.timeout} seconds"
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError) as error:
        result["completed"] = False
        result["error"] = f"{type(error).__name__}: {error}"

    result["elapsed_seconds"] = round(time.time() - started, 2)
    results_dir = ROOT / "test_results"
    results_dir.mkdir(exist_ok=True)
    result_path = results_dir / f"t2i_steps_{args.steps}_{int(started)}.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result_path": str(result_path), **result}, ensure_ascii=False, indent=2))
    return 0 if result.get("completed") and result.get("status", {}).get("status_str") == "success" else 2


if __name__ == "__main__":
    sys.exit(main())
