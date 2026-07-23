# Models, locations, and integrity

All local model files belong under <code>ComfyUI/models</code>. The workflow
metadata expects the GGUF files in <code>diffusion_models</code>; do not move
them to <code>models/unet</code>.

The entire model directory is ignored by both the project and ComfyUI Git
rules. Model weights must remain local and must not be committed, staged, or
uploaded to GitHub.

## Installed files

Sizes below use ordinary decimal MB/GB units. The SHA-256 values were verified
locally on 2026-07-23.

| Component | Local path | Size | SHA-256 |
| --- | --- | ---: | --- |
| FLUX.2 Klein 4B Base Q3_K_M | <code>ComfyUI/models/diffusion_models/flux-2-klein-base-4b-Q3_K_M.gguf</code> | 2.12 GB | <code>88b7f7191ece79596be78a69fddcba45bd93d01ffaae2751b231ee5e8ee23be8</code> |
| FLUX.2 Klein 4B Base Q4_K_M | <code>ComfyUI/models/diffusion_models/flux-2-klein-base-4b-Q4_K_M.gguf</code> | 2.60 GB | <code>8348ff1f2b3ac3cf9eb62f38322fcbb6d92811d39aa036d0671cf7bef9411266</code> |
| FLUX.2 Klein 4B Base Q5_K_M | <code>ComfyUI/models/diffusion_models/flux-2-klein-base-4b-Q5_K_M.gguf</code> | 3.07 GB | <code>1252620f38658466150f60654a3430ff31ed516f29fc837ee3db66713ee3474c</code> |
| Qwen3 4B text encoder | <code>ComfyUI/models/text_encoders/qwen_3_4b.safetensors</code> | 8.04 GB | <code>6c671498573ac2f7a5501502ccce8d2b08ea6ca2f661c458e708f36b36edfc5a</code> |
| FLUX2 VAE | <code>ComfyUI/models/vae/flux2-vae.safetensors</code> | 336 MB | <code>868fe7b343cc8f3a19dbcfcafbc3d5f888802be3f89bd81b65b3621a066ce8f3</code> |

To check a model after moving or downloading it, run this from PowerShell and
compare the value with the table:

~~~powershell
Get-FileHash -Algorithm SHA256 .\ComfyUI\models\diffusion_models\flux-2-klein-base-4b-Q4_K_M.gguf
~~~

If one hash is wrong, replace only that file. Do not delete the working model
set or duplicate the weights elsewhere.

## Choosing a GGUF variant

| Variant | Intended use | Verified locally |
| --- | --- | --- |
| Q4_K_M | Default balanced choice. | 512 × 512 and 640 × 640 at 40 steps; 1280 × 720 at 20 steps. |
| Q5_K_M | Slightly higher-precision optional variant. | 512 × 512 at 40 steps. It used more VRAM than Q4. |
| Q3_K_M | Lower-memory, coarser quantization for high-resolution attempts. | 1920 × 1088 at 20 steps. |

Q3 enabled the highest tested resolution on this machine, but its coarser
quantization may trade detail for memory headroom. A successful test is not a
guarantee for every prompt, image, or number of steps. Q5 is not a way to raise
the maximum resolution; it required more VRAM in the tested configuration.

## Pinned sources

The verified files were obtained from these pinned source revisions:

| Artifact | Repository | Revision |
| --- | --- | --- |
| Base GGUF variants | [unsloth/FLUX.2-klein-base-4B-GGUF](https://huggingface.co/unsloth/FLUX.2-klein-base-4B-GGUF) | <code>5fd6513800b1f13016fab83600b392a35f29d56d</code> |
| Qwen3 text encoder | [Comfy-Org/vae-text-encorder-for-flux-klein-4b](https://huggingface.co/Comfy-Org/vae-text-encorder-for-flux-klein-4b) | <code>8556e4d870cda7c53c7942b190bfeea5be9bd411</code> |
| FLUX2 VAE | [Comfy-Org/vae-text-encorder-for-flux-klein-4b](https://huggingface.co/Comfy-Org/vae-text-encorder-for-flux-klein-4b) | <code>a9e4ca87c16db4c4e1a16406a9ddb300ab0ae246</code> |

The table and pinned source revisions above are the current integrity record.
If an optional recovery snapshot is created later, it will record the same
paths, byte sizes, source revisions, and hashes.
