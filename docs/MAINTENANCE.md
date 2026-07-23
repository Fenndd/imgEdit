# Maintenance and safe updates

## Diagnostics

Run <code>CHECK_SYSTEM.bat</code> to display the GPU state, embedded Python
and relevant package versions, plus the ComfyUI and ComfyUI-GGUF commits. The
script is diagnostic only.

Launcher and update logs are stored in <code>logs/</code>. They remain on the
computer but are ignored by Git.

## Use only the project launchers

Use these files for this setup:

| File | Use |
| --- | --- |
| <code>START_FLUX2_BALANCED.bat</code> | Normal local generation and editing. |
| <code>START_FLUX2_MINIMUM_VRAM.bat</code> | Recovery profile after an out-of-memory error. |
| <code>OPEN_OUTPUT_FOLDER.bat</code> | Opens generated images. |
| <code>CHECK_SYSTEM.bat</code> | Read-only configuration check. |

Do not use the generic <code>run_nvidia_gpu*.bat</code>, <code>run_cpu.bat</code>,
or the stock
<code>update/update_comfyui_and_python_dependencies.bat</code> for this
verified FLUX/GGUF installation. Those scripts do not represent the tested
profile, and the stock dependency updater can replace the bundled PyTorch
version.

## Update carefully

<code>UPDATE_COMFYUI.bat</code> fast-forwards the local ComfyUI repository and
installs its declared requirements without forcing a PyTorch upgrade.
<code>UPDATE_CUSTOM_NODES.bat</code> updates only ComfyUI-GGUF and its
requirements.

Both update scripts intentionally access the network. They can change the
tested software state even though they avoid a forced PyTorch upgrade.

Before updating:

1. Keep a copy of your important output images and workflows.
2. Close ComfyUI.
3. Run only one update script at a time.
4. Read the log in <code>logs/</code>.
5. Run a small 512 × 512 test before relying on the new version for long work.

If the update causes a regression, use [RECOVERY.md](RECOVERY.md) to return to
the audited revisions.

## Page file script

<code>CONFIGURE_PAGEFILE_32_48GB.ps1</code> changes Windows system settings.
It must be started with administrator rights, requires a restart, and should
only be considered if the current page file is insufficient. The validated
machine already had a fixed 30 GB page file, so this script was not needed for
the documented tests.

## Git hygiene

The following local folders are intentionally ignored:

- <code>ComfyUI/models/</code> — model weights;
- <code>python_embeded/</code> — portable Python, PyTorch, and CUDA libraries;
- <code>downloads/</code> — installers and archives;
- <code>logs/</code> — launch and update logs.

Before committing, check <code>git status</code>. Never force-add model files,
the portable runtime, or logs.
