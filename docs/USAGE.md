# Using the local FLUX.2 Klein setup

## Start ComfyUI

Use <code>START_FLUX2_BALANCED.bat</code> for normal work. It starts the local
UI at <code>http://127.0.0.1:8188</code>, enables dynamic VRAM handling,
reserves 1 GB of VRAM, disables cloud API nodes, and writes a log under
<code>logs/</code>.

Use <code>START_FLUX2_MINIMUM_VRAM.bat</code> only after a CUDA
out-of-memory error. It additionally enables the low-memory profile, moves the
VAE to the CPU, and disables previews. It is a recovery option rather than the
recommended default, and it has not been benchmarked separately.

All generated images are written to <code>ComfyUI/output</code>. Run
<code>OPEN_OUTPUT_FOLDER.bat</code> to open that folder.

## Open a workflow

The five supplied workflows are stored in
<code>ComfyUI/user/default/workflows/FLUX2_KLEIN_4B</code>. In ComfyUI, choose
<strong>Workflow → Open</strong> or drag a workflow JSON (or a generated PNG
with embedded metadata) onto the canvas.

| File | Purpose |
| --- | --- |
| <code>01_TEXT_TO_IMAGE_MAX_QUALITY.json</code> | Text-to-image with the FLUX.2 Klein Base GGUF model. |
| <code>02_SINGLE_IMAGE_EDIT.json</code> | One source image and one requested edit. |
| <code>03_MULTI_REFERENCE_EDIT.json</code> | A source composition plus two extra references. |
| <code>04_MASKED_LOCAL_EDIT.json</code> | A local edit constrained by a mask; the original is composited back outside the mask. |
| <code>05_IDENTITY_PRESERVATION.json</code> | Three references and a mask for conservative, identity-preserving local edits. |

The default model choice is Q4. Open the large central subgraph in a workflow
to change the prompt, seed, dimensions, sampling steps, CFG/guidance, or GGUF
variant.

## Workflow guidance

### Text to image

Start with Q4 at 512 × 512 and 40 steps. Change one variable at a time when
comparing results: prompt, seed, model, size, or sampling settings.

### Single-image editing

Load one image and describe one concrete modification. A focused instruction is
more reliable than a list of unrelated changes. For example:

> Change only the color of the mug from red to dark blue. Preserve its exact
> shape, position, lighting, table and background.

Use a separate pass for the next complex change instead of asking one run to
change face, pose, clothes, background, and lighting at once.

### Multiple references

The three inputs in workflows 03 and 05 are intended for:

1. the original composition;
2. face or appearance; and
3. clothes, style, or an additional view.

All reference paths use native <code>ReferenceLatent</code> chains. If a second
or third reference is unnecessary, open the subgraph and bypass both matching
<code>ReferenceLatent</code> nodes with <code>Ctrl+B</code>.

### Masked editing and identity preservation

In workflows 04 and 05, white mask pixels permit changes and black pixels
preserve the original. Use a mask with the same aspect ratio as the source
image.

- A separately created grayscale PNG is read from its red channel.
- In ComfyUI's Mask Editor, use the alpha channel.
- The workflow grows the mask by 16 px and softens its edge before the final
  composite.
- Do not include a face in the mask unless the face is meant to change.

The final <code>ImageCompositeMasked</code> node restores original pixels
outside the softened mask. This was verified by the masked-edit tests.

## Reproducibility

For the closest repeatable result, retain the workflow JSON, model variant,
prompt, seed, dimensions, steps, and CFG/guidance. A Q4 512 × 512 test
repeated with the same seed produced identical pixels on the verified machine.

ComfyUI-generated PNGs normally embed prompt and workflow metadata. Dragging
such a PNG onto the canvas is a convenient way to restore the graph that made
it.

## Resolution and model choice

Q4 is the stable default. Q5 is an optional higher-precision variant for
512 × 512 work, not a replacement for Q4. Q3 is the lower-memory option that
was used for the high-resolution tests. See [MODELS.md](MODELS.md) for the
trade-offs and [VALIDATION.md](VALIDATION.md) for the exact tested envelope.
