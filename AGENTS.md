# Agent Development Notes for Prompt Image Organizer

## Project Overview

Prompt Image Organizer is a Python CLI tool that intelligently organizes AI-generated images into session folders based on their prompts and creation time. The project uses modern Python tooling with `uv` for dependency management and follows semantic versioning.

## Architecture & Core Components

### Package Structure
```
src/prompt_image_organizer/
├── __init__.py          # Package initialization and exports
├── __main__.py          # CLI entry point for `python -m` usage
├── core.py              # Core business logic and algorithms
└── cli.py               # Command-line interface and argument parsing
```

### Key Modules

#### `core.py` - Core Business Logic
- **File Operations**: `scan_files()`, `move_file_worker()`, `get_image_files()`
- **Time Grouping**: `group_by_time()` - Groups files by configurable time gaps
- **Prompt Clustering**: `cluster_prompts()` - Clusters by prompt similarity using difflib
- **Processing Pipeline**: `process_clusters()` - Main orchestration function
- **Utilities**: `sanitize_for_folder()`, `extract_prompt()`, `similar()`

#### `cli.py` - Command Line Interface
- **Configuration**: `parse_config()` - Parses CLI args and environment variables
- **Help System**: `print_help()` - Comprehensive help text
- **Main Entry**: `main()` - CLI entry point

## Development Environment

### Python Version
- **Required**: Python >= 3.12
- **Virtual Environment**: Use uv for dependency management
- **Package Manager**: uv (as evidenced by uv.lock file)

### Dependencies
- **Core Dependencies**:
  - tqdm >= 4.67.1 (for progress bars)
- **Development Dependencies**: black, flake8, mypy, pytest, coverage, etc.

### Setup Commands
```bash
# Clone and setup
git clone <repository-url>
cd prompt-image-organizer

# Install dependencies
uv sync

# Install package in development mode
uv pip install -e .

# Verify installation
uv run prompt-image-organizer --help
```

## Code Style & Standards

### Python Code
- **Type Hints**: Always use type hints for function parameters and return values
- **Docstrings**: Use Google-style docstrings for all public functions and classes
- **Line Length**: Maximum 88 characters (Black default)
- **Import Order**: Use isort for consistent import ordering
- **Formatting**: Use Black for code formatting

### Naming Conventions
- **Files**: snake_case for Python files
- **Functions**: snake_case
- **Classes**: PascalCase
- **Constants**: UPPER_SNAKE_CASE
- **Variables**: snake_case

## Key Algorithms & Logic

### 1. File Scanning (`scan_files`)
- Scans directory for image files (.png, .jpg, .jpeg, .webp)
- Extracts modification time and prompts from filenames
- Returns list of tuples: `(filename, mtime, prompt)`

### 2. Time-Based Grouping (`group_by_time`)
- Groups files into batches based on configurable time gaps
- Uses `timedelta` for time calculations
- Default gap: 60 minutes (configurable via `--gap`)

### 3. Prompt Clustering (`cluster_prompts`)
- Uses `difflib.SequenceMatcher` for similarity calculation
- Groups files with similar prompts within each time batch
- Similarity threshold: 0.8 (configurable via `--sim`)
- Optional cluster size limit (configurable via `--limit`)

### 4. File Processing (`process_clusters`)
- Creates session folders with descriptive names
- Uses `ThreadPoolExecutor` for concurrent file operations
- Implements progress tracking with `tqdm`
- Handles dry-run mode for safe previewing

## Configuration System

### Command Line Arguments
- `--gap MIN`: Time gap in minutes (default: 60)
- `--sim F`: Similarity threshold 0-1 (default: 0.8)
- `--limit N`: Max files per session (default: unlimited)
- `--workers N`: Concurrent operations (default: 8)
- `--debug`: Verbose logging mode
- `-x`: Actually move files (default: dry run)

### Environment Variables
- `SRC_DIR`: Source directory
- `DST_DIR`: Destination directory
- `SESSION_GAP_MINUTES`: Time gap override
- `PROMPT_SIMILARITY`: Similarity threshold override
- `SESSION_CLUSTER_LIMIT`: Cluster size limit override
- `SESSION_WORKERS`: Worker count override

## Progress Tracking System

### Implementation Details
- Uses `tqdm` for progress bars (gracefully handles missing dependency)
- Tracks total progress across all files
- Shows per-file progress updates
- Displays processing rate and ETA
- Clean display without verbose output (unless `--debug`)

### Progress Bar Features
- **Width**: 120 columns for better visibility
- **Format**: `{l_bar}{bar}| {n_fmt}/{total_fmt} files [{elapsed}<{remaining}, {rate_fmt}]`
- **Dynamic**: Resizes based on terminal width
- **Real-time**: Updates for each file processed

## Error Handling

### Principles
- **Never Assume**: Never assume error causes based on superficial similarities
- **Investigate Systematically**: Look for root causes, not symptoms
- **Graceful Degradation**: Handle errors without crashing the application
- **User-Friendly Messages**: Provide clear error messages to users

### Error Types
- **File Errors**: Handle missing, corrupted, or inaccessible files
- **Format Errors**: Handle unsupported image formats
- **Memory Errors**: Handle large file processing gracefully
- **Permission Errors**: Handle file permission issues

## Testing Strategy

### Testing Principles
- **Behavior-Focused**: Write tests that focus on behavior, not implementation details
- **Avoid Brittle Tests**: Avoid brittle tests (like SQL string assertions)
- **Test-Driven Development**: Encourage TDD when appropriate
- **Coverage Goal**: Aim for >80% coverage

### Unit Tests
- Write tests for all public functions
- Test individual functions and classes
- Test edge cases and error conditions

### Integration Tests
- Test image processing workflows
- Test complete workflows
- Test performance with large datasets

### Test Output
- Place test outputs outside project root to avoid clutter
- Test coverage: Aim for >80% coverage

### Running Tests
```bash
# With unittest
uv run python -m unittest discover tests -v

# With pytest
uv run pytest tests/ -v

# With coverage
uv run pytest --cov=src/prompt_image_organizer tests/
```

### CLI Usage
- **Entry Point**: Use the installed CLI command:
  - `uv run prompt-image-organizer --help`
  - Or after install: `prompt-image-organizer --help`
- **Module Style**: `uv run python -m prompt_image_organizer --help` also works

## Code Quality Standards

### Core Principles
- **O.O.D.A.**: Observe, Orient, Decide, Act
- **One Change at a Time**: Make one logical change per commit
- **Test Before Committing**: Ensure changes work as expected
- **Commit Each Change Separately**: Keep changes isolated
- **Roll Back if Needed**: If a change doesn't fix the issue, roll back

### Code Style & Structure
- **Clarity Over Brevity**: Clarity is more important than brevity
- **Explicit Over Implicit**: Explicit is WAY better than implicit
- **Empathy**: Help the next developer who looks at this code
- **Separate Concerns**: Keep linting/docs changes separate from logic changes in VCS

### Code Quality
- **Linting**: Use flake8, mypy, and other linting tools
- **Formatting**: Use Black for consistent formatting
- **Pre-commit Hooks**: Set up pre-commit hooks for quality checks

### Type Safety & Documentation
- **Never Assume**: Never assume object behavior without type hints
- **Review APIs**: Review APIs before implementation
- **Maintain Documentation**: Keep clear documentation up to date
- **Type Hints**: Use comprehensive type hints for all function parameters and return values
- **Examples**: Include usage examples in docstrings

### Documentation

#### Code Documentation
- **Public APIs**: Document all public functions and classes
- **Complex Logic**: Add inline comments for complex algorithms
- **Type Hints**: Use comprehensive type hints
- **Examples**: Include usage examples in docstrings

#### Project Documentation
- **README**: Keep README.md updated with usage instructions
- **API Docs**: Generate API documentation
- **Examples**: Provide working examples in `examples/` directory

## Performance Considerations

### Image Processing
- **Lazy Loading**: Load images only when needed
- **Batch Processing**: Process multiple images efficiently
- **Memory Usage**: Monitor and optimize memory usage
- **Progress Feedback**: Provide progress updates for long operations

### Optimization
- **Profiling**: Profile code for bottlenecks
- **Caching**: Cache expensive operations where appropriate
- **Parallel Processing**: Use multiprocessing for CPU-intensive tasks

## Security Considerations

### File Operations
- **Path Validation**: Validate file paths to prevent directory traversal
- **File Permissions**: Respect file permissions
- **Safe File Operations**: Use safe file handling practices

### Data Privacy
- **User Data**: Handle user data responsibly
- **Logging**: Avoid logging sensitive information
- **Configuration**: Store configuration securely

## Deployment & Distribution

### Packaging
- **PyPI Ready**: Structure for PyPI distribution
- **Wheel Building**: Ensure wheel compatibility
- **Dependencies**: Minimize external dependencies

### Distribution
- **Version Management**: Use semantic versioning
- **Changelog**: Maintain a changelog
- **Release Notes**: Document breaking changes

## Maintenance

### Regular Tasks
- **Dependency Updates**: Regularly update dependencies
- **Security Audits**: Audit dependencies for security issues
- **Performance Monitoring**: Monitor performance metrics
- **Documentation Updates**: Keep documentation current

### Code Review
- **Peer Review**: Have code reviewed by team members
- **Automated Checks**: Use CI/CD for automated quality checks
- **Standards Compliance**: Ensure compliance with project standards

## Best Practices

### Development Approach
- **Be Pragmatic**: Balance best practices with real-world constraints
- **SOLID Principles**: Follow SOLID principles where practical
- **Value-Added Practices**: Recommend practices that add value without unnecessary overhead
- **Project Context**: Consider project context (public vs. private, client vs. internal)
- **Precision**: Do exactly what the task requires
- **Ask for Clarification**: Ask for clarification if something seems wrong
- **Verify Changes**: Verify changes through testing

## Communication

### Team Communication
- **Clear Commit Messages**: Write descriptive commit messages
- **Issue Tracking**: Use issue tracking for bugs and features
- **Documentation**: Keep documentation up to date
- **Knowledge Sharing**: Share knowledge and best practices

### User Communication
- **Error Messages**: Provide clear, actionable error messages
- **Progress Updates**: Keep users informed of long-running operations
- **Help Text**: Provide comprehensive help and usage information

## Development Workflow Process

### Process Steps
1. **OODA** - Observe, Orient, Decide, Act
2. **Describe** - What to accomplish and how, get approval before proceeding
3. **Implementation** - Write the code
4. **Tests** - Write tests following good patterns (avoid brittle tests)
5. **Commit** - When tests pass, write good commit message and commit
6. **Document** - Explain implementation and what was tested
7. **Log** - Write down in cursorrules folder as ongoing log for reference
8. **Push** - Prompt to push
9. **URLs** - When pushed, provide commit URL and PR URL

### Key Principles
- Always get approval before proceeding with implementation
- Write tests that focus on behavior, not implementation details
- Avoid brittle tests (like SQL string assertions)
- Document what was implemented and tested
- Keep ongoing log for future reference

### Before Starting
1. Ensure you're using Python 3.12+
2. Create and activate the virtual environment: `uv venv`
3. Install dependencies: `uv sync`
4. Install the package in development mode: `uv pip install -e .`

### Code Changes
1. **One Change at a Time**: Make one logical change per commit
2. **Test Before Committing**: Ensure changes work as expected
3. **Separate Commits**: Keep linting/docs changes separate from logic changes
4. **Roll Back if Needed**: If a change doesn't fix the issue, roll back

## Image Processing Rules

### File Handling
- **Supported Formats**: Define supported image formats clearly
- **Error Handling**: Graceful handling of corrupted or unsupported files
- **Memory Management**: Process large images efficiently
- **Progress Tracking**: Use tqdm for long-running operations

### Data Management
- **Sessions**: Store session data in `sessions/` directory
- **Temporary Files**: Clean up temporary files after processing
- **Output Organization**: Structure output directories logically

---

*This document provides comprehensive guidance for AI agents working on the Prompt Image Organizer project. It covers architecture, development practices, testing strategies, and maintenance procedures.*
