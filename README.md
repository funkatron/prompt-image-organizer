# Prompt Image Organizer

Organize AI-generated images into dated session folders with safe, neutral names.

## What It Does

The tool scans a source directory, groups image files by time and prompt similarity,
and organizes them into a destination tree like:

```text
DEST_DIR/
  20260313/
    20260313-1103-session-002-054/
      63630146fe54c453e9d4ad0d98d0a5de.png
      792cec298af48d2e83303ff9e0558d16.png
  _all/
    63630146fe54c453e9d4ad0d98d0a5de.png -> ../20260313/20260313-1103-session-002-054/63630146fe54c453e9d4ad0d98d0a5de.png
```

Key behaviors:

- Groups images by time proximity and prompt similarity
- Creates dated folders as `YYYYMMDD/<session_folder>/`
- Uses safe neutral default session names
- Renames moved files to content-hash filenames
- Maintains a top-level `_all/` directory of symlinks to every organized image
- Supports dry-run preview, cleanup of broken `_all` links, and backfill of `_all`

## Installation

### Development Setup

```bash
git clone <repository-url>
cd prompt-image-organizer
uv sync
uv pip install -e .
```

### From PyPI

```bash
pip install prompt-image-organizer
```

## Quick Start

```bash
# Preview the organization plan
uv run prompt-image-organizer ./source-images ./image-sessions

# Actually move files
uv run prompt-image-organizer ./source-images ./image-sessions -x

# Open the destination folder when done
uv run prompt-image-organizer ./source-images ./image-sessions -x --open
```

If you omit `DST_DIR`, the tool uses `<SRC_DIR>/sessions`.

## Common Commands

```bash
# Change the time gap and similarity threshold
uv run prompt-image-organizer ./imgs ./out --gap 45 --sim 0.9 -x

# Cap session size
uv run prompt-image-organizer ./imgs ./out --limit 100 -x

# Show verbose progress and per-file actions
uv run prompt-image-organizer ./imgs ./out --debug -x

# Remove broken links from DEST_DIR/_all
uv run prompt-image-organizer ./imgs ./out --cleanup-broken-links -x

# Rebuild missing _all links from existing dated session folders
uv run prompt-image-organizer ./imgs ./out --backfill-all-links -x
```

## Folder And File Naming

### Default Session Folder Pattern

The default session folder pattern is:

```text
{datetime}-session-{cluster_index:03d}-{count_padded}
```

Example:

```text
20260313-1103-session-002-054
```

This keeps default naming neutral and avoids semantic interpretation of filenames.

### Destination Layout

Each session is placed under a date folder:

```text
YYYYMMDD/<session_folder>/
```

Example:

```text
20260313/20260313-1103-session-002-054/
```

### Moved File Names

When files are actually moved, each image is renamed to:

```text
<md5-of-file-contents><original-extension>
```

Examples:

```text
63630146fe54c453e9d4ad0d98d0a5de.png
63630146fe54c453e9d4ad0d98d0a5de-02.png
```

The `-02` suffix is only added when two files in the same destination would
otherwise collide.

### Aggregate `_all` Directory

The top-level `_all/` directory contains symlinks to every moved image across
all sessions. This gives you one flat directory for browsing or indexing while
preserving the dated session structure underneath.

## Configuration

- `--gap MIN`: maximum time gap in minutes for batching images
- `--sim F`: prompt similarity threshold from `0` to `1`
- `--limit N`: maximum images per session when provided
- `--workers N`: number of concurrent file moves
- `--pattern P`: custom session folder pattern
- `--cleanup-broken-links`: remove broken symlinks from `DST_DIR/_all`
- `--backfill-all-links`: rebuild missing `_all` symlinks from existing sessions
- `--open`: open the destination folder when processing succeeds
- `--debug`: verbose logging
- `-x`: actually move files; without this flag the tool performs a dry run

Environment variables:

- `SRC_DIR`
- `DST_DIR`
- `SESSION_GAP_MINUTES`
- `PROMPT_SIMILARITY`
- `SESSION_CLUSTER_LIMIT`
- `SESSION_WORKERS`
- `SESSION_FOLDER_PATTERN`

## Custom Folder Patterns

Patterns use Python `str.format` placeholders. Available values:

- `date`: earliest image date as `YYYYMMDD`
- `time`: earliest image time as `HHMM`
- `datetime`: earliest image timestamp as `YYYYMMDD-HHMM`
- `slug`: sanitized prompt slug
- `base_slug`: sanitized slug without checksum
- `count`: cluster size as an integer
- `count_padded`: cluster size with zero padding
- `cluster_index`: cluster number within the batch, starting at `1`
- `batch_index`: batch number, starting at `1`
- `checksum`: checksum suffix without the leading dash
- `checksum_suffix`: checksum suffix including the leading dash when present

For safety, folder pattern output must resolve to a single folder name. Absolute
paths, separators, and traversal segments like `..` are rejected.

## Python API

```python
from datetime import timedelta

from prompt_image_organizer import group_by_time, print_summary, process_clusters, scan_files

file_data = scan_files("./images")
batches = group_by_time(file_data, timedelta(minutes=60))

config = {
    "src_dir": "./images",
    "dst_dir": "./sessions",
    "gap": timedelta(minutes=60),
    "sim_thresh": 0.8,
    "cluster_size_limit": None,
    "dry_run": True,
    "workers": 8,
    "debug": False,
    "folder_pattern": "{datetime}-session-{cluster_index:03d}-{count_padded}",
}

session_count, total_files, move_errors = process_clusters(batches, config)
print_summary(session_count, total_files, move_errors, config["dry_run"])
```

## How It Works

1. Scans the source directory for image files (`.png`, `.jpg`, `.jpeg`, `.webp`)
2. Extracts prompts from filenames for similarity clustering
3. Groups nearby files into time batches
4. Splits each batch into prompt-similar clusters
5. Creates a dated session directory for each cluster
6. On `-x`, moves files into those sessions with hash-based filenames
7. Maintains `_all/` symlinks for every organized image

## Requirements

- Python 3.12+
- `tqdm` for progress bars

## Development

### Running Tests

```bash
uv run pytest -q
```

### Code Quality

```bash
uv run black src/ tests/
uv run flake8 src/ tests/
uv run mypy src/
```

## Project Structure

```text
prompt-image-organizer/
├── src/prompt_image_organizer/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   └── core.py
├── tests/
├── examples/
├── CHANGELOG.md
├── pyproject.toml
└── README.md
```

## License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE) for details.
