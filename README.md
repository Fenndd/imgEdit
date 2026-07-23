# Local FLUX.2 Klein 4B with ComfyUI

This repository documents a verified Windows 11 installation for local FLUX.2
Klein 4B image generation and editing. Generation runs through ComfyUI on this
computer; the provided launchers bind the UI to <code>127.0.0.1:8188</code> and
disable cloud API nodes.

## Quick start

1. Run <code>START_FLUX2_BALANCED.bat</code>.
2. Open a workflow from
   <code>ComfyUI/user/default/workflows/FLUX2_KLEIN_4B</code> using
   <strong>Workflow → Open</strong>, or drag the JSON file into ComfyUI.
3. Find generated images in <code>ComfyUI/output</code>, or run
   <code>OPEN_OUTPUT_FOLDER.bat</code>.

If ComfyUI reports an out-of-memory error, close it and use
<code>START_FLUX2_MINIMUM_VRAM.bat</code>. That profile is an emergency
fallback; the balanced profile is the verified default.

## Documentation

- [Usage and workflows](docs/USAGE.md)
- [Models and integrity checks](docs/MODELS.md)
- [Verified configuration and test results](docs/VALIDATION.md)
- [Maintenance and safe updates](docs/MAINTENANCE.md)
- [Recovery and optional snapshots](docs/RECOVERY.md)

## Repository boundaries

- Model weights remain only in <code>ComfyUI/models</code> and must never be
  committed or uploaded to GitHub.
- The portable Python runtime, downloads, and logs are local-only and ignored
  by Git.
- No recovery snapshot is retained by default. An optional local snapshot can
  be created deliberately; the documents linked above are the current
  instructions.
- The nested <code>ComfyUI/</code> repository retains its own upstream
  documentation and is not rewritten by this project documentation.
