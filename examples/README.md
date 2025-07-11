# Prompt Image Organizer Examples

This directory contains examples of how to use the `prompt-image-organizer` package.

## Basic Usage

### Command Line Interface

```bash
# Basic usage - dry run
python3 -m prompt_image_organizer ./images ./sessions

# Actually move files
python3 -m prompt_image_organizer ./images ./sessions -x

# Custom time gap (30 minutes)
python3 -m prompt_image_organizer ./images ./sessions --gap 30 -x

# Higher similarity threshold
python3 -m prompt_image_organizer ./images ./sessions --sim 0.9 -x

# Limit cluster size
python3 -m prompt_image_organizer ./images ./sessions --limit 50 -x

# More workers for faster processing
python3 -m prompt_image_organizer ./images ./sessions --workers 16 -x
```

### Environment Variables

You can also configure the tool using environment variables:

```bash
export SRC_DIR="./my_images"
export DST_DIR="./organized_sessions"
export SESSION_GAP_MINUTES=45
export PROMPT_SIMILARITY=0.85
export SESSION_CLUSTER_LIMIT=100
export SESSION_WORKERS=12

python3 -m prompt_image_organizer -x
```

### Python API

```python
from prompt_image_organizer import (
    scan_files,
    group_by_time,
    cluster_prompts,
    process_clusters,
    print_summary
)
from datetime import timedelta

# Scan files
file_data = scan_files("./images")

# Group by time (60 minute gaps)
batches = group_by_time(file_data, timedelta(minutes=60))

# Process with custom config
config = {
    "src_dir": "./images",
    "dst_dir": "./sessions",
    "gap": timedelta(minutes=60),
    "sim_thresh": 0.8,
    "cluster_size_limit": None,
    "dry_run": True,
    "workers": 8
}

session_count, total_files, move_errors = process_clusters(batches, config)
print_summary(session_count, total_files, move_errors, config["dry_run"])
```

## File Naming Conventions

The tool expects image files with prompts in the filename. It extracts the prompt by removing numbering suffixes:

- `my_prompt_1.png` → prompt: `my_prompt`
- `another_prompt_2.jpg` → prompt: `another_prompt`
- `complex_prompt_with_spaces_3.webp` → prompt: `complex_prompt_with_spaces`

## Session Folder Structure

Organized files will be placed in session folders with the naming pattern:
`session_YYYYMMDD_HHMM_sanitized-prompt`

Example:
```
sessions/
├── session_20241201_1430_cat-in-garden/
│   ├── cat_in_garden_1.png
│   ├── cat_in_garden_2.jpg
│   └── cat_in_garden_3.webp
├── session_20241201_1500_dog-on-beach/
│   ├── dog_on_beach_1.png
│   └── dog_on_beach_2.jpg
└── session_20241201_1600_landscape/
    ├── landscape_1.png
    ├── landscape_2.jpg
    └── landscape_3.webp
```

## Supported Image Formats

- PNG (`.png`)
- JPEG (`.jpg`, `.jpeg`)
- WebP (`.webp`)

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `--gap` | 60 minutes | Maximum time gap between files to group in same session |
| `--sim` | 0.8 | Similarity threshold for prompt clustering (0-1) |
| `--limit` | unlimited | Maximum files per session cluster |
| `--workers` | 8 | Number of concurrent file operations |
| `-x` | False | Actually move files (default is dry run) |