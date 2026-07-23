# Local FLUX.2 Klein 4B and Atlas Cloud with ComfyUI

This repository provides two isolated ComfyUI profiles:

- **Local FLUX.2 Klein 4B** runs entirely on this computer at
  <code>127.0.0.1:8188</code>. Its launchers disable cloud API nodes.
- **Atlas Cloud** runs at <code>127.0.0.1:8189</code> with its own inputs,
  outputs, models, user data, workflow copies, and custom nodes. It never uses
  the local FLUX.2 model directory.

## Local quick start

1. Run <code>START_FLUX2_BALANCED.bat</code>.
2. Open a workflow from
   <code>ComfyUI/user/default/workflows/FLUX2_KLEIN_4B</code> using
   <strong>Workflow → Open</strong>, or drag the JSON file into ComfyUI.
3. Find generated images in <code>ComfyUI/output</code>, or run
   <code>OPEN_OUTPUT_FOLDER.bat</code>.

If ComfyUI reports an out-of-memory error, close it and use
<code>START_FLUX2_MINIMUM_VRAM.bat</code>. That profile is an emergency
fallback; the balanced profile is the verified default.

## Atlas Cloud quick start

1. Create an Atlas Cloud key in the Atlas console.
2. Run <code>SET_ATLAS_CLOUD_API_KEY.bat</code> and paste the key into the
   secure prompt. The key is encrypted for the current Windows account and is
   never written into a workflow.
3. Optionally run <code>TEST_ATLAS_CLOUD_CONNECTION.bat</code>. It verifies
   the key without creating a paid generation.
4. Run <code>START_ATLAS_CLOUD.bat</code>.
5. In the cloud UI, open a supplied workflow from
   <code>Workflow &gt; Open</code>. The first launch copies the templates into
   the isolated Atlas Cloud workspace.

Leave the <strong>API key</strong> field in the <strong>AtlasCloud Client</strong>
node blank. The launcher provides the key only to the Atlas Cloud process.
See [Atlas Cloud setup and workflows](docs/ATLAS_CLOUD.md) for details.

## Documentation

- [Usage and workflows](docs/USAGE.md)
- [Atlas Cloud setup and workflows](docs/ATLAS_CLOUD.md)
- [Models and integrity checks](docs/MODELS.md)
- [Verified configuration and test results](docs/VALIDATION.md)
- [Maintenance and safe updates](docs/MAINTENANCE.md)
- [Recovery and optional snapshots](docs/RECOVERY.md)

## Repository boundaries

- Model weights remain only in <code>ComfyUI/models</code> and must never be
  committed or uploaded to GitHub.
- The portable Python runtime, downloads, and logs are local-only and ignored
  by Git.
- Atlas Cloud credentials, vendor nodes, inputs, outputs, and runtime state are
  local-only and ignored by Git. The tracked files in <code>AtlasCloud/workflows</code>
  are templates only; they contain no credential.
- No recovery snapshot is retained by default. An optional local snapshot can
  be created deliberately; the documents linked above are the current
  instructions.
- The nested <code>ComfyUI/</code> repository retains its own upstream
  documentation and is not rewritten by this project documentation.
