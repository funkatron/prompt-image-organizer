# Prompt Image Organizer

Organize AI-generated images into session folders based on their prompts and creation time.

## What it does

This tool helps you organize AI-generated images (like those from Draw Things, Stable Diffusion, etc.) by grouping them into session folders based on:

- **Time proximity**: Images created within a specified time gap are grouped into the same session
- **Prompt similarity**: Images with similar prompts are clustered into the same session
- **Creation order**: Maintains chronological organization within sessions

## Features

- **Smart clustering**: Groups images by prompt similarity and time gaps into session folders
- **Flexible configuration**: Adjustable time gaps and similarity thresholds
- **Safe operations**: Dry-run mode to preview changes before making them
- **Progress tracking**: Visual progress bars showing per-file progress
- **Concurrent processing**: Multi-threaded file operations for speed

## Installation

### Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd prompt-image-organizer

# Install dependencies with uv
uv sync

# Install package in development mode
uv pip install -e .
```

### From PyPI (when published)

```bash
pip install prompt-image-organizer
```

## Usage

### Command Line Interface

```bash
# Preview what would be organized (dry run)
uv run prompt-image-organizer ./source-images ./session-folders

# Actually organize the images into session folders
uv run prompt-image-organizer ./source-images ./session-folders -x

# Or if installed globally
prompt-image-organizer ./source-images ./session-folders -x
```

### Advanced options

```bash
# Custom time gap (45 minutes) and similarity threshold (0.9)
uv run prompt-image-organizer ./imgs ./out --gap 45 --sim 0.9 -x

# Limit cluster size to 100 images per session folder
uv run prompt-image-organizer ./imgs ./out --limit 100 -x

# Use more worker threads for faster processing
uv run prompt-image-organizer ./imgs ./out --workers 12 -x

# Enable debug mode to see detailed session and file operation logs
uv run prompt-image-organizer ./imgs ./out --debug -x
```

### Environment variables

You can also configure via environment variables:

```bash
export SRC_DIR="./source-images"
export DST_DIR="./session-folders"
export SESSION_GAP_MINUTES=60
export PROMPT_SIMILARITY=0.8
export SESSION_CLUSTER_LIMIT=100
export SESSION_WORKERS=8

uv run prompt-image-organizer -x
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

## Configuration

- **`--gap MIN`**: Maximum time gap in minutes to group images (default: 60)
- **`--sim F`**: Prompt similarity threshold 0-1 (default: 0.8)
- **`--limit N`**: Maximum images per session folder (default: unlimited)
- **`--workers N`**: Number of concurrent file operations (default: 8)
- **`--debug`**: Enable verbose logging of session details and file operations
- **`-x`**: Actually move files (default: dry run)

When you omit the destination argument and the `DST_DIR` environment variable,
files are organized into `<SRC_DIR>/sessions` by default (for the default
`SRC_DIR` of `.`, this resolves to `./sessions`).

## How it works

1. **Scans** your source directory for image files (.png, .jpg, .jpeg, .webp)
2. **Extracts** prompts from filenames (removes numbering suffixes)
3. **Groups** images by time gaps into batches
4. **Clusters** each batch by prompt similarity
5. **Creates** session folders with descriptive names
6. **Moves** files into organized session structure

## Session folder naming

Session folders are named using the pattern:
```
YYYYMMDD-HHMM-slug-count/
```

- `YYYYMMDD-HHMM`: Timestamp of the earliest image in the cluster.
- `slug`: Up to three meaningful prompt tokens (stopwords removed, max 18 chars).
- `count`: Zero-padded file count (e.g., `007`).
- If multiple clusters share the same timestamp and slug, a three-letter checksum
  is inserted before the count: `YYYYMMDD-HHMM-slug-abc-007/`.

Example: `20241201-1430-cat-sitting-chair-004/`

Customize the naming pattern with `--pattern` or the `SESSION_FOLDER_PATTERN`
environment variable. Patterns use Python `str.format` placeholders:

- `date`: Earliest image date (`YYYYMMDD`)
- `time`: Earliest image time (`HHMM`)
- `datetime`: Combined timestamp (`YYYYMMDD-HHMM`)
- `slug`: Sanitized prompt slug (checksum added automatically if needed)
- `base_slug`: Sanitized slug without checksum
- `count`: Cluster size as an integer
- `count_padded`: Cluster size with zero padding (`003`)
- `cluster_index`: Cluster number within the batch (1-based)
- `batch_index`: Batch number (1-based)
- `checksum`: Three-letter checksum, if applied
- `checksum_suffix`: `-abc` when checksum is present, otherwise an empty string

Default pattern: `{datetime}-{slug}{checksum_suffix}-{count_padded}`

## File naming conventions

The tool expects image files with prompts in the filename. It extracts the prompt by removing numbering suffixes:

- `my_prompt_1.png` → prompt: `my_prompt`
- `another_prompt_2.jpg` → prompt: `another_prompt`
- `complex_prompt_with_spaces_3.webp` → prompt: `complex_prompt_with_spaces`

## Requirements

- Python 3.12+
- tqdm (for progress bars)

## Development

### Running Tests

```bash
# Run all tests with unittest
uv run python -m unittest discover tests -v

# Run tests with pytest (if installed)
uv run pytest tests/ -v

# Run tests with coverage
uv run pytest --cov=src/prompt_image_organizer tests/
```

### Code Quality

```bash
# Format code with Black
uv run black src/ tests/

# Lint with Flake8
uv run flake8 src/ tests/

# Type checking with mypy
uv run mypy src/
```

### Test Structure

- **`tests/test_utils.py`**: Unit tests for utility functions
- **`tests/test_integration.py`**: Integration tests for full workflow
- **`tests/test_cli.py`**: CLI and command line interface tests
- **`tests/conftest.py`**: Pytest fixtures and configuration

### Test Coverage

The test suite covers:
- ✅ Utility functions (sanitize_for_folder, extract_prompt, similar, etc.)
- ✅ File operations (get_image_files, move_file_worker)
- ✅ Time-based grouping (group_by_time)
- ✅ Prompt clustering (cluster_prompts)
- ✅ Configuration parsing (parse_config)
- ✅ CLI functionality (argument parsing, help text)
- ✅ Error handling (invalid inputs, permission errors)
- ✅ Edge cases (empty directories, no images)
- ✅ Full workflow (dry run and actual file movement)

## Project Structure

```
prompt-image-organizer/
├── src/prompt_image_organizer/
│   ├── __init__.py          # Package entry point
│   ├── __main__.py          # CLI entry point for python -m
│   ├── core.py              # Core functionality
│   └── cli.py               # Command-line interface
├── tests/                   # Test suite
├── examples/                # Usage examples
├── pyproject.toml          # Project configuration
└── README.md               # This file
```

## License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE) for details.
