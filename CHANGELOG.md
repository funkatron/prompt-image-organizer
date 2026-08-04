# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-08-04

### Added
- Per-session `manifest.json` recording each moved file's original name,
  extracted prompt, and modification time alongside its stored hash name,
  making moves auditable and reversible
- Dry runs now print the actual plan: each session folder with sample
  original filenames, plus a hint that `--move` applies it
- `--move` as the self-documenting spelling of `-x`, and an explicit
  `--dry-run` flag so scripts can state the default
- `pio` as a short CLI alias for `prompt-image-organizer`
- `{session_index}` folder pattern placeholder: a run-global session
  counter that never repeats, unlike the per-batch `{cluster_index}`
- Warnings on invalid environment variable values instead of silent
  fallback to defaults

### Changed
- Default session folder pattern is now
  `{datetime}-session-{session_index:03d}-x{count_padded}`; session numbers
  no longer repeat within a run and the file count reads as a count
- `--cleanup-broken-links` and `--backfill-all-links` are standalone
  maintenance operations: they run and exit instead of also organizing
  whatever is in the source directory
- Dry runs no longer touch the filesystem: the destination directory is
  not created and file contents are not read (hash names show as `<md5>`
  placeholders in `--debug` output)
- Fatal errors go to stderr, and argument errors point at `-h`
- The progress bar only appears for real moves, not dry runs

### Removed
- Vestigial "install tqdm" hint (`tqdm` is a hard dependency)

## [0.1.2] - 2026-03-13

### Added
- Safer neutral default session naming with `{datetime}-session-{cluster_index:03d}-{count_padded}`
- Dated destination layout as `YYYYMMDD/<session-folder>/`
- Top-level `_all/` aggregate symlink directory
- `--cleanup-broken-links` to remove broken `_all` symlinks
- `--backfill-all-links` to rebuild missing `_all` symlinks from existing sessions
- `--open` to open the destination folder after a successful run
- Debug scan progress output for larger source directories

### Changed
- Actual moved filenames now use MD5 content hashes plus the original extension
- Dry-run folder name reservation now matches real execution
- Folder pattern validation now rejects traversal, separators, and paths outside the destination root
- CLI parsing now validates `--gap`, `--sim`, `--limit`, and `--workers` before processing

### Fixed
- Backfill no longer creates duplicate `_all` symlinks for targets that are already linked

## [0.1.1] - 2025-01-11

### Changed
- Progress bar now tracks total progress across all clusters instead of per-cluster progress
- Improved user experience with a single progress bar showing overall file processing status
- Clean progress bar display with verbose logging only under `--debug`
- Enhanced progress bar updates with current file context
- Wider progress bar formatting for better visibility

### Added
- `--debug` flag for verbose session and file operation logging
- GitHub repository setup
- Documentation updates

## [0.1.0] - 2025-01-11

### Added
- Initial release
- Smart image clustering by prompt similarity and time gaps
- Modern Python package structure with `src/prompt_image_organizer/`
- CLI entry point via `prompt-image-organizer`
- Dry-run preview mode
- Progress tracking with `tqdm`
- Multi-threaded file operations
- CLI and environment-variable configuration
- Test suite covering core functionality
