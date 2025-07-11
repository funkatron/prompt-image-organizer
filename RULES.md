# Prompt Image Organizer Project Rules

## Project Overview
This is a Python project for organizing AI-generated images by their prompts and creation time. The project uses modern Python tooling with uv for dependency management.

## Development Environment

### Python Version
- **Required**: Python >= 3.12
- **Virtual Environment**: Use uv for dependency management
- **Package Manager**: uv (as evidenced by uv.lock file)

### Dependencies
- **Core Dependencies**:
  - tqdm >= 4.67.1 (for progress bars)
- **Development Dependencies**: black, flake8, mypy, pytest, coverage, etc.

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

## Project Structure

### Current Structure
```
prompt-image-organizer/
├── src/
│   └── prompt_image_organizer/
│       ├── __init__.py
│       ├── __main__.py
│       ├── core.py
│       └── cli.py
├── tests/
├── examples/
├── pyproject.toml
├── README.md
├── RULES.md
├── uv.lock
└── .gitignore
```

## Development Workflow

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

### Testing Strategy
- **Unit Tests**: Write tests for all public functions
- **Integration Tests**: Test image processing workflows
- **Test Output**: Place test outputs outside project root to avoid clutter
- **Test Coverage**: Aim for >80% coverage
- **Run tests**: `uv run python -m unittest discover tests -v` or `uv run pytest tests/`

### CLI Usage
- **Entry Point**: Use the installed CLI command:
  - `uv run prompt-image-organizer --help`
  - Or after install: `prompt-image-organizer --help`
- **Module Style**: `uv run python -m prompt_image_organizer --help` also works

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

## Error Handling

### Principles
- **Never Assume**: Don't assume error causes based on superficial similarities
- **Investigate Systematically**: Look for root causes, not symptoms
- **Graceful Degradation**: Handle errors without crashing the application
- **User-Friendly Messages**: Provide clear error messages to users

### Error Types
- **File Errors**: Handle missing, corrupted, or inaccessible files
- **Format Errors**: Handle unsupported image formats
- **Memory Errors**: Handle large file processing gracefully
- **Permission Errors**: Handle file permission issues

## Documentation

### Code Documentation
- **Public APIs**: Document all public functions and classes
- **Complex Logic**: Add inline comments for complex algorithms
- **Type Hints**: Use comprehensive type hints
- **Examples**: Include usage examples in docstrings

### Project Documentation
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

## Quality Assurance

### Code Quality
- **Linting**: Use flake8, mypy, and other linting tools
- **Formatting**: Use Black for consistent formatting
- **Pre-commit Hooks**: Set up pre-commit hooks for quality checks

### Testing
- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test complete workflows
- **Edge Cases**: Test edge cases and error conditions
- **Performance Tests**: Test performance with large datasets

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