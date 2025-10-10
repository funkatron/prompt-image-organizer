# Prompt Image Organizer Examples

This directory focuses on practical, scenario-based examples. For full documentation, installation, configuration, and API usage, see `README.md`.

## Quick Start Recipes

```bash
# Preview (dry run)
uv run prompt-image-organizer ./images ./sessions

# Actually move files
uv run prompt-image-organizer ./images ./sessions -x

# Higher similarity threshold and larger gap (e.g., full-day sessions)
uv run prompt-image-organizer ./images ./sessions --gap 1440 --sim 0.5 -x

# More workers for faster I/O-bound moves
uv run prompt-image-organizer ./images ./sessions --workers 16 -x
```

## Real-World Scenarios

### 1) Organize a large export by day (common for mobile/Draw Things dumps)
```bash
uv run prompt-image-organizer ./dump ./sessions --gap 1440 --sim 0.5
```
- Groups images into daily sessions and clusters similar prompts.
- Start in dry-run to preview folder structure; add `-x` to move.

### 2) Group by working session (short bursts)
```bash
uv run prompt-image-organizer ./imgs ./sessions --gap 30 --sim 0.8 -x
```
- Treats images within 30 minutes as a session; higher similarity reduces mixing.

### 3) Cap session size for extremely large clusters
```bash
uv run prompt-image-organizer ./imgs ./sessions --limit 100 -x
```
- Prevents any single session from growing unmanageably large.

## Troubleshooting Examples

### See what the tool is doing
```bash
uv run prompt-image-organizer ./imgs ./sessions --debug
```
- Shows session creation and file operations. Errors are always shown.

### Progress bar clarity
- The bar shows per-file progress (X/Y files). If your terminal truncates output, scroll to the bottom or run in a larger window.

### Common pitfalls
- `--gap` accepts an integer (minutes), not `1m`. Use `--gap 1`.
- Without `-x`, it is a dry run (no file moves). Add `-x` to move.
- If performance is slow on network drives, try reducing `--workers`.

## Minimal Python API Pointer

For a complete Python API example, see `README.md` (section: Python API). Below is a minimal sketch:

```python
from prompt_image_organizer import scan_files, group_by_time, process_clusters, print_summary
from datetime import timedelta

files = scan_files("./images")
batches = group_by_time(files, timedelta(minutes=60))
config = {
    "src_dir": "./images",
    "dst_dir": "./sessions",
    "gap": timedelta(minutes=60),
    "sim_thresh": 0.8,
    "cluster_size_limit": None,
    "dry_run": True,
    "workers": 8,
}
session_count, total_files, move_errors = process_clusters(batches, config)
print_summary(session_count, total_files, move_errors, config["dry_run"])
```

---

Tips:
- Start with a dry run, review the proposed folder layout, then add `-x`.
- Use `--debug` when you need detailed insight; otherwise keep output clean.
