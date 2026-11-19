# Verified configuration and test results

This page records observations from a full local validation completed on
2026-07-23. They describe this computer and this software state; they are not
hardware requirements or a guarantee that every prompt will fit in memory.

## Validation machine

| Item | Verified value |
| --- | --- |
| Operating system | Windows 11 Home, build 26200, x64 |
| CPU | AMD Ryzen 5 5600H, 6 cores / 12 threads |
| RAM | 14.9 GB (13.86 GiB reported by Windows) |
| GPU | NVIDIA GeForce RTX 3060 Laptop GPU, 6 GB VRAM |
| Driver / CUDA support | 581.80 / CUDA 13.0 |
| Page file | Fixed 30 GB on <code>C:</code> |
| Runtime | Portable Python 3.13.12 |

## Verified software state

| Component | Version or commit |
| --- | --- |
| ComfyUI | <code>2e47082c8ed1d1a0fe54add57f98b63433cfacbb</code> |
| PyTorch | <code>2.13.0+cu130</code> |
| ComfyUI-GGUF | <code>6ea2651e7df66d7585f6ffee804b20e92fb38b8a</code> |
| ComfyUI-Manager | 4.2.2 |
| GGUF / workflow templates / comfy-kitchen | 0.19.0 / 0.11.15 / 0.2.22 |

The normal launcher exposes ComfyUI only at <code>127.0.0.1:8188</code>,
does not use <code>--listen</code>, and disables cloud API nodes. Manager is
configured for offline mode during ordinary local use.

## Successful local runs

Peak VRAM values are rounded to ordinary GB units. Raw test records are written
locally to <code>test_results/</code>, which is not tracked by Git.

| Scenario | Resolution / steps | Time | Peak VRAM | Result |
| --- | --- | ---: | ---: | --- |
| Smoke text-to-image | 512 × 512 / 1 | 79.50 s | 4.3 GB | Success |
| Q4 text-to-image | 512 × 512 / 40 | 133.19 s | 4.5 GB | Success |
| Q4 repeat with the same seed | 512 × 512 / 40 | 137.30 s | 4.5 GB | Pixel-identical to the first Q4 result |
| Single-image edit | 512 × 512 / 20 | 103.56 s | 4.8 GB | Success |
| Three-reference edit | 512 × 512 / 20 | 154.82 s | 4.9 GB | Success |
| Masked local edit | 512 × 512 / 20 | 102.86 s | 4.9 GB | Zero changed pixels outside the mask |
| Identity-preserving masked edit | 512 × 512 / 20 | 141.63 s | 4.8 GB | Zero changed pixels outside the mask |
| Q5 text-to-image | 512 × 512 / 40 | 153.02 s | 5.3 GB | Success |
| Q4 higher resolution | 640 × 640 / 40 | 134.21 s | 4.9 GB | Success |
| Q4 720p-class | 1280 × 720 / 20 | 192.78 s | 5.1 GB | Success |
| Q3 1080p-class | 1920 × 1088 / 20 | 227.31 s | 5.6 GB | Success; image inspected visually |

The largest observed RAM value was about 14.9 GB, so close other demanding
programs before long generations.

## Practical limits

- The verified defaults are Q4, 512 × 512, 40 steps, CFG 5, and seed
  <code>123456789</code>.
- Q4 was also verified at 640 × 640 for 40 steps and 1280 × 720 for 20 steps.
- Q5 was verified only at 512 × 512 for 40 steps.
- Q3 was verified at 1920 × 1088 for 20 steps. This is a 1080p-class size that
  is divisible by 16.
- 1920 × 1088 at 40 steps was not verified. Increase resolution or steps one
  at a time and keep other applications closed.
- The low-VRAM launcher is available if a normal run runs out of memory, but it
  was not separately benchmarked.

All five workflow JSON files were also opened through ComfyUI's Workflows
panel after the run. Each loaded without missing nodes or import errors.
