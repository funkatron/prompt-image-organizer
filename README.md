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
- **Progress tracking**: Visual progress bars for long operations
- **Concurrent processing**: Multi-threaded file operations for speed

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd prompt-image-organizer

# Install dependencies
uv sync
```

## Usage

### Basic usage

```bash
# Preview what would be organized (dry run)
python prompt-image-organizer.py ./source-images ./session-folders

# Actually organize the images into session folders
python prompt-image-organizer.py ./source-images ./session-folders -x
```

### Advanced options

```bash
# Custom time gap (45 minutes) and similarity threshold (0.9)
python prompt-image-organizer.py ./imgs ./out --gap 45 --sim 0.9 -x

# Limit cluster size to 100 images per session folder
python prompt-image-organizer.py ./imgs ./out --limit 100 -x

# Use more worker threads for faster processing
python prompt-image-organizer.py ./imgs ./out --workers 12 -x
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

python prompt-image-organizer.py
```

## Configuration

- **`--gap MIN`**: Maximum time gap in minutes to group images (default: 60)
- **`--sim F`**: Prompt similarity threshold 0-1 (default: 0.8)
- **`--limit N`**: Maximum images per session folder (default: unlimited)
- **`--workers N`**: Number of concurrent file operations (default: 8)
- **`-x`**: Actually move files (default: dry run)

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
session_YYYYMMDD_HHMM_prompt-name/
```

Example: `session_20241201_1430_a-cat-sitting-on-a-chair/`

## Requirements

- Python 3.12+
- tqdm (for progress bars)

## Development

### Running Tests

```bash
# Run all tests
python run_tests.py

# Run tests with coverage
python run_tests.py --coverage

# Create test data
python run_tests.py --create-test-data

# Using pytest directly
pytest tests/

# Using pytest with coverage
pytest --cov=group_images tests/
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

## License

MIT License

Copyright Edward Finkler (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


