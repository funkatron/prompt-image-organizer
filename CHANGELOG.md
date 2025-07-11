# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub repository setup
- Comprehensive documentation updates

## [0.1.0] - 2025-01-11

### Added
- **Initial release** of Prompt Image Organizer
- **Smart image clustering** by prompt similarity and time gaps
- **Modern Python package structure** with `src/prompt_image_organizer/`
- **Comprehensive type hints** throughout the codebase
- **CLI interface** with `prompt-image-organizer` command
- **Safe operations** with dry-run mode for previewing changes
- **Progress tracking** with tqdm progress bars
- **Multi-threaded file operations** for fast processing
- **Flexible configuration** via command-line arguments and environment variables
- **Comprehensive test suite** with 41 tests covering all functionality
- **Code quality tools** integration (Black, Flake8, mypy)
- **Documentation** including README, examples, and usage guides

### Features
- **File scanning**: Automatically detects image files (.png, .jpg, .jpeg, .webp)
- **Prompt extraction**: Intelligently extracts prompts from filenames
- **Time-based grouping**: Groups images by configurable time gaps
- **Similarity clustering**: Clusters images by prompt similarity with adjustable threshold
- **Session folder creation**: Creates organized session folders with descriptive names
- **Error handling**: Graceful handling of file errors, permissions, and edge cases
- **Environment variables**: Full configuration via environment variables
- **Python API**: Programmatic access to all core functionality

### Technical Details
- **Python 3.12+** requirement
- **uv** for dependency management
- **Modern packaging** with pyproject.toml
- **Type safety** with comprehensive type hints
- **Test coverage** with unittest and pytest support
- **Code formatting** with Black and linting with Flake8
- **Type checking** with mypy

### Usage Examples
```bash
# Basic usage
uv run prompt-image-organizer ./images ./sessions

# With custom settings
uv run prompt-image-organizer ./images ./sessions --gap 30 --sim 0.9 -x

# Using environment variables
export SESSION_GAP_MINUTES=45
export PROMPT_SIMILARITY=0.85
uv run prompt-image-organizer ./images ./sessions -x
```

### File Naming Conventions
The tool expects image files with prompts in the filename:
- `my_prompt_1.png` → prompt: `my_prompt`
- `another_prompt_2.jpg` → prompt: `another_prompt`
- `complex_prompt_with_spaces_3.webp` → prompt: `complex_prompt_with_spaces`

### Session Folder Structure
Organized files are placed in session folders with the naming pattern:
`session_YYYYMMDD_HHMM_sanitized-prompt/`

Example: `session_20241201_1430_a-cat-sitting-on-a-chair/`

---

## Release Notes

### v0.1.0 - Initial Release
This is the initial release of Prompt Image Organizer, a Python tool for organizing AI-generated images by their prompts and creation time. The tool provides smart clustering, safe operations, and a modern CLI interface.

**Key Features:**
- ✅ Smart image clustering by prompt similarity and time gaps
- ✅ Safe dry-run mode for previewing changes
- ✅ Multi-threaded file operations for speed
- ✅ Comprehensive type hints and testing
- ✅ Modern Python package structure
- ✅ Flexible configuration via CLI and environment variables

**Installation:**
```bash
# Development
git clone https://github.com/funkatron/prompt-image-organizer.git
cd prompt-image-organizer
uv sync
uv pip install -e .

# Usage
uv run prompt-image-organizer --help
```

**Breaking Changes:** None (initial release)

**Migration Guide:** Not applicable (initial release)