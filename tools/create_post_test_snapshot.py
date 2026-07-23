"""Create a compact, reproducible snapshot of the verified local installation.

The snapshot records the source revisions, custom-node source, runtime setup,
configuration, workflows and hashes of model files.  It intentionally never
copies model weights, the portable Python runtime, or the ComfyUI source tree.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT_NAME = "2026-07-23_tz_audited_snapshot"
COMFY = ROOT / "ComfyUI"
GGUF_NODE = COMFY / "custom_nodes" / "ComfyUI-GGUF"

SOURCE_REPOSITORIES = {
    "comfyui": "https://github.com/Comfy-Org/ComfyUI.git",
    "comfyui_gguf": "https://github.com/city96/ComfyUI-GGUF.git",
}
MODEL_DOWNLOAD_SOURCES = {
    "base_gguf": {
        "repository": "https://huggingface.co/unsloth/FLUX.2-klein-base-4B-GGUF",
        "revision": "5fd6513800b1f13016fab83600b392a35f29d56d",
    },
    "text_encoder": {
        "repository": "https://huggingface.co/Comfy-Org/vae-text-encorder-for-flux-klein-4b",
        "revision": "8556e4d870cda7c53c7942b190bfeea5be9bd411",
    },
    "vae": {
        "repository": "https://huggingface.co/Comfy-Org/vae-text-encorder-for-flux-klein-4b",
        "revision": "a9e4ca87c16db4c4e1a16406a9ddb300ab0ae246",
    },
}


def command(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = (result.stdout + result.stderr).strip()
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(args)}\n{output}")
    return output


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_file(source: Path, destination_dir: Path) -> None:
    if source.is_file():
        shutil.copy2(source, destination_dir / source.name)


def copy_runtime_file(source: Path, destination: Path, snapshot: Path) -> dict[str, object] | None:
    """Copy one small configuration file and return its reproducibility record."""
    if not source.is_file():
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return {
        "source_relative_to_project": source.relative_to(ROOT).as_posix(),
        "snapshot_relative_path": destination.relative_to(snapshot).as_posix(),
        "size_bytes": source.stat().st_size,
        "sha256": sha256(source),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default=DEFAULT_SNAPSHOT_NAME, help="Folder name below backup/.")
    args = parser.parse_args()
    if Path(args.name).name != args.name:
        parser.error("--name must be a simple folder name")
    snapshot = ROOT / "backup" / args.name
    if snapshot.exists():
        raise SystemExit(f"Snapshot already exists: {snapshot}")

    snapshot.mkdir(parents=True)
    workflows_destination = snapshot / "workflows"
    launchers_destination = snapshot / "launchers_and_tools"
    docs_destination = snapshot / "documentation"
    tests_destination = snapshot / "test_results"
    runtime_destination = snapshot / "runtime_configuration"
    workflows_destination.mkdir()
    launchers_destination.mkdir()
    docs_destination.mkdir()
    runtime_destination.mkdir()

    shutil.copytree(COMFY / "user" / "default" / "workflows" / "FLUX2_KLEIN_4B", workflows_destination / "FLUX2_KLEIN_4B")
    if (ROOT / "test_results").is_dir():
        shutil.copytree(ROOT / "test_results", tests_destination)

    for name in (
        "START_FLUX2_BALANCED.bat",
        "START_FLUX2_MINIMUM_VRAM.bat",
        "UPDATE_COMFYUI.bat",
        "UPDATE_CUSTOM_NODES.bat",
        "OPEN_OUTPUT_FOLDER.bat",
        "CHECK_SYSTEM.bat",
        "CHECK_SYSTEM.ps1",
        "CONFIGURE_PAGEFILE_32_48GB.ps1",
        ".gitignore",
    ):
        copy_file(ROOT / name, launchers_destination)
    for name in (
        "generate_flux2_workflows.py",
        "create_post_test_snapshot.py",
        "run_flux2_t2i_test.py",
        "run_flux2_edit_test.py",
        "run_flux2_multi_reference_test.py",
        "run_flux2_identity_test.py",
    ):
        copy_file(ROOT / "tools" / name, launchers_destination)
    copy_file(ROOT / "README.md", docs_destination)
    if (ROOT / "docs").is_dir():
        shutil.copytree(ROOT / "docs", docs_destination / "docs")

    runtime_sources = {
        "comfyui_requirements": (COMFY / "requirements.txt", "comfyui_requirements.txt"),
        "manager_requirements": (COMFY / "manager_requirements.txt", "manager_requirements.txt"),
        "gguf_requirements": (GGUF_NODE / "requirements.txt", "gguf_requirements.txt"),
        "manager_config": (COMFY / "user" / "__manager" / "config.ini", "manager_config.ini"),
        "manager_channels": (COMFY / "user" / "__manager" / "channels.list", "manager_channels.list"),
        "comfy_settings": (COMFY / "user" / "default" / "comfy.settings.json", "comfy.settings.json"),
        "extra_model_paths": (COMFY / "extra_model_paths.yaml", "extra_model_paths.yaml"),
    }
    runtime_configuration = {
        name: record
        for name, (source, destination_name) in runtime_sources.items()
        if (record := copy_runtime_file(source, runtime_destination / destination_name, snapshot)) is not None
    }

    model_paths = {
        "base_gguf_q3_k_m": COMFY / "models" / "diffusion_models" / "flux-2-klein-base-4b-Q3_K_M.gguf",
        "base_gguf_q4_k_m": COMFY / "models" / "diffusion_models" / "flux-2-klein-base-4b-Q4_K_M.gguf",
        "base_gguf_q5_k_m": COMFY / "models" / "diffusion_models" / "flux-2-klein-base-4b-Q5_K_M.gguf",
        "qwen3_4b_text_encoder": COMFY / "models" / "text_encoders" / "qwen_3_4b.safetensors",
        "flux2_vae": COMFY / "models" / "vae" / "flux2-vae.safetensors",
    }
    models = {
        key: {
            "path_relative_to_project": str(path.relative_to(ROOT)),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for key, path in model_paths.items()
    }

    comfy_commit = command(["git", "-c", f"safe.directory={COMFY.as_posix()}", "-C", str(COMFY), "rev-parse", "HEAD"])
    comfy_status = command([
        "git", "-c", f"safe.directory={COMFY.as_posix()}",
        "-c", f"core.excludesFile={(ROOT / '.gitignore').as_posix()}",
        "-C", str(COMFY), "status", "--short",
    ])
    gguf_commit = command(["git", "-c", f"safe.directory={GGUF_NODE.as_posix()}", "-C", str(GGUF_NODE), "rev-parse", "HEAD"])
    gguf_status = command([
        "git", "-c", f"safe.directory={GGUF_NODE.as_posix()}",
        "-c", f"core.excludesFile={(ROOT / '.gitignore').as_posix()}",
        "-C", str(GGUF_NODE), "status", "--short",
    ])
    pip_freeze = command([sys.executable, "-m", "pip", "freeze"])

    manifest = {
        "format_version": 2,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "project_root": str(ROOT),
        "portable_python": sys.version,
        "runtime": {
            "python_executable_relative_to_project": "python_embeded/python.exe",
            "python_version_used_to_create_snapshot": sys.version,
            "pip_freeze_file": "PIP_FREEZE.txt",
            "configuration_directory": "runtime_configuration",
            "configuration_files": runtime_configuration,
        },
        "repositories": {
            "ComfyUI": {
                "repository_url": SOURCE_REPOSITORIES["comfyui"],
                "path_relative_to_project": COMFY.relative_to(ROOT).as_posix(),
                "commit": comfy_commit,
                "git_status": comfy_status,
            },
            "ComfyUI-GGUF": {
                "repository_url": SOURCE_REPOSITORIES["comfyui_gguf"],
                "path_relative_to_project": GGUF_NODE.relative_to(ROOT).as_posix(),
                "commit": gguf_commit,
                "git_status": gguf_status,
            },
        },
        "custom_nodes": [
            {
                "name": "ComfyUI-GGUF",
                "repository_url": SOURCE_REPOSITORIES["comfyui_gguf"],
                "path_relative_to_project": GGUF_NODE.relative_to(ROOT).as_posix(),
                "commit": gguf_commit,
                "git_status": gguf_status,
                "requirements_snapshot_key": "gguf_requirements",
            }
        ],
        "model_download_sources": MODEL_DOWNLOAD_SOURCES,
        "comfyui_commit": comfy_commit,
        "comfyui_git_status": comfy_status,
        "comfyui_gguf_commit": gguf_commit,
        "comfyui_gguf_git_status": gguf_status,
        "models": models,
        "model_weights_copied": False,
    }
    (snapshot / "SNAPSHOT_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (snapshot / "PIP_FREEZE.txt").write_text(pip_freeze + "\n", encoding="utf-8")
    (snapshot / "README.txt").write_text(
        "Verified local FLUX.2 Klein installation snapshot.\n"
        "Contains workflow, launcher/tool, test-result, runtime-configuration, and current documentation copies.\n"
        "It intentionally contains no model weights, portable Python, or ComfyUI source tree.\n"
        "Use SNAPSHOT_MANIFEST.json to restore source revisions and verify model files.\n",
        encoding="utf-8",
    )
    print(snapshot)


if __name__ == "__main__":
    main()
