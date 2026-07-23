# Recovery and optional snapshots

## Current state

No <code>backup/</code> snapshot is retained in this project. Removing that
folder does not affect ComfyUI, the portable Python runtime, installed models,
workflows, or the launch scripts.

The current recovery record lives in this documentation:

- [MODELS.md](MODELS.md) contains local model paths, hashes, and pinned sources.
- [VALIDATION.md](VALIDATION.md) records the verified ComfyUI and
  ComfyUI-GGUF commits.
- <code>ComfyUI/user/default/workflows/FLUX2_KLEIN_4B</code> contains the
  working workflow JSON files.

## Recover a working installation

1. Close ComfyUI. Copy any output images and personal workflows you want to
   preserve before changing files.
2. Check a suspected model with <code>Get-FileHash -Algorithm SHA256</code>
   and compare it with [MODELS.md](MODELS.md). Replace only a damaged file.
3. If an update or local source edit caused a regression, save your changes
   first and restore the audited source revisions. Checkout replaces the
   current source state.

~~~powershell
git -C ComfyUI checkout 2e47082c8ed1d1a0fe54add57f98b63433cfacbb
git -C ComfyUI\custom_nodes\ComfyUI-GGUF checkout 6ea2651e7df66d7585f6ffee804b20e92fb38b8a
~~~

4. Do not blindly upgrade PyTorch to repair a problem. Start with
   <code>CHECK_SYSTEM.bat</code>, compare the installed versions with
   [VALIDATION.md](VALIDATION.md), and identify the failed component.
5. Restore a workflow copy if needed, then run
   <code>START_FLUX2_BALANCED.bat</code>. Use the minimum-VRAM launcher only
   after an out-of-memory error.

## Create a snapshot only when useful

<code>tools/create_post_test_snapshot.py</code> can create a compact local
snapshot under <code>backup/</code> when you explicitly run it. It copies the
root README, current <code>docs/</code>, workflow copies, tools, test results,
and small runtime configuration files. It never copies model weights, portable
Python, or the ComfyUI source tree.

The script calculates SHA-256 hashes for every installed model, so it reads
many gigabytes of local files. Run it only when you intentionally want a new
audit or recovery record, not as routine maintenance.

~~~powershell
.\python_embeded\python.exe .\tools\create_post_test_snapshot.py --name 2026-07-23_my_snapshot
~~~
