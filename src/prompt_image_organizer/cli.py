"""Command-line interface for prompt image organizer."""

import argparse
import os
import subprocess
import sys
from datetime import timedelta
from typing import Dict, Any

from .core import (
    backfill_all_symlinks,
    cleanup_broken_symlinks,
    get_env_int,
    get_env_float,
    scan_files,
    group_by_time,
    process_clusters,
    print_summary,
    DEFAULT_FOLDER_PATTERN,
)


class HelpPointerArgumentParser(argparse.ArgumentParser):
    """Argument parser whose error messages point at the full help text."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(
            2,
            f"{self.prog}: error: {message}\n"
            f"Run '{self.prog} -h' for full help.\n",
        )


def print_help() -> None:
    """Print help message for the CLI."""
    print("""
Prompt Image Organizer

Usage:
  prompt-image-organizer [SRC_DIR] [DST_DIR] [options]

Arguments:
  SRC_DIR           Source image directory; only its top level is scanned,
                    subfolders are ignored (default: $SRC_DIR or current dir)
  DST_DIR           Destination session directory (default: $DST_DIR or SRC_DIR/sessions)

Options:
  --gap MIN         Max gap (minutes) to group into a batch/session [env: SESSION_GAP_MINUTES, default: 60]
  --sim F           Prompt similarity threshold [0-1, env: PROMPT_SIMILARITY, default: 0.8]
  --limit N         Maximum cluster (session) size [env: SESSION_CLUSTER_LIMIT, default: unlimited]
  --workers N       Number of concurrent file moves (default: 8)
  --pattern P       Folder naming pattern (default: {datetime}-session-{session_index:03d}-x{count_padded})
  --cleanup-broken-links
                    Remove broken symlinks from DST_DIR/_all, then exit (standalone; does not organize)
  --backfill-all-links
                    Rebuild missing `_all` symlinks from existing session folders, then exit (standalone)
  --open            Open the destination sessions folder when processing succeeds
  --debug           Enable verbose logging (shows session details and file operations)
  -x, --move        Actually move files (default: dry run)
  --dry-run         Preview without moving files (the default; provided so scripts can be explicit)
  -h, --help        Show this help message

Examples:
  prompt-image-organizer ./imgs ./out --gap 45 --workers 12
  prompt-image-organizer ./imgs ./out --sim 0.9 --limit 100 --move
  prompt-image-organizer -h
""")


def parse_config() -> Dict[str, Any]:
    """Parse command line arguments and environment variables.

    Returns:
        Configuration dictionary
    """
    parser = HelpPointerArgumentParser(prog="prompt-image-organizer", add_help=False)
    parser.add_argument('src', nargs='?', help="Source directory")
    parser.add_argument('dst', nargs='?', help="Destination directory")
    parser.add_argument('--gap', type=int, help="Gap in minutes (default 60)")
    parser.add_argument('--sim', type=float, help="Prompt similarity threshold (default 0.8)")
    parser.add_argument('--limit', type=int, help="Maximum session (cluster) size (default: unlimited)")
    parser.add_argument('--workers', type=int, help="Number of concurrent file moves (default: 8)")
    parser.add_argument(
        '--pattern',
        help=f"Folder naming pattern (default: {DEFAULT_FOLDER_PATTERN})"
    )
    parser.add_argument(
        '--cleanup-broken-links',
        action='store_true',
        help="Remove broken symlinks from DST_DIR/_all, then exit without organizing",
    )
    parser.add_argument(
        '--backfill-all-links',
        action='store_true',
        help="Rebuild missing `_all` symlinks from existing sessions, then exit without organizing",
    )
    parser.add_argument(
        '--open',
        action='store_true',
        help="Open the destination sessions folder when processing succeeds",
    )
    parser.add_argument('--debug', action='store_true', help="Enable verbose logging")
    parser.add_argument('-x', '--move', dest='move', action='store_true',
                        help="Actually move files (default: dry run)")
    parser.add_argument('--dry-run', dest='dry_run', action='store_true',
                        help="Preview without moving files (the default)")
    parser.add_argument('-h', '--help', action='store_true', help="Show help")
    args = parser.parse_args()

    if args.help:
        print_help()
        sys.exit(0)

    src_dir = args.src or os.environ.get("SRC_DIR", ".")

    if args.dst:
        dst_dir = args.dst
    else:
        env_dst = os.environ.get("DST_DIR")
        dst_dir = env_dst if env_dst is not None else os.path.join(src_dir, "sessions")
    gap_min = args.gap if args.gap is not None else get_env_int("SESSION_GAP_MINUTES", 60)
    sim_thresh = args.sim if args.sim is not None else get_env_float("PROMPT_SIMILARITY", 0.8)
    cluster_size_limit = args.limit if args.limit is not None else get_env_int("SESSION_CLUSTER_LIMIT", 0) or None
    if args.move and args.dry_run:
        parser.error("--move (-x) and --dry-run are mutually exclusive")
    dry_run = not args.move
    workers = args.workers if args.workers is not None else get_env_int("SESSION_WORKERS", 8)
    debug = args.debug
    folder_pattern = args.pattern or os.environ.get("SESSION_FOLDER_PATTERN", DEFAULT_FOLDER_PATTERN)
    cleanup_broken_links = args.cleanup_broken_links
    backfill_all_links = args.backfill_all_links
    open_when_done = args.open

    if gap_min < 0:
        parser.error("--gap must be greater than or equal to 0")
    if not 0 <= sim_thresh <= 1:
        parser.error("--sim must be between 0 and 1 inclusive")
    if cluster_size_limit is not None and cluster_size_limit <= 0:
        parser.error("--limit must be greater than 0")
    if workers < 1:
        parser.error("--workers must be greater than or equal to 1")

    return {
        "src_dir": src_dir,
        "dst_dir": dst_dir,
        "gap": timedelta(minutes=gap_min),
        "sim_thresh": sim_thresh,
        "cluster_size_limit": cluster_size_limit,
        "dry_run": dry_run,
        "workers": workers,
        "debug": debug,
        "folder_pattern": folder_pattern,
        "cleanup_broken_links": cleanup_broken_links,
        "backfill_all_links": backfill_all_links,
        "open_when_done": open_when_done,
    }


def open_directory(path: str) -> None:
    """Open a directory in the platform file browser."""
    if sys.platform == "darwin":
        subprocess.run(["open", path], check=True)
        return
    if os.name == "nt":
        os.startfile(path)
        return

    subprocess.run(["xdg-open", path], check=True)


def open_destination_if_present(dst_dir: str) -> None:
    """Open the destination folder, or explain why it cannot be opened.

    Dry runs no longer create the destination, so it may not exist yet.
    """
    if not os.path.isdir(dst_dir):
        print(f"Note: destination '{dst_dir}' does not exist yet; nothing to open.")
        return
    open_directory(dst_dir)


def main() -> None:
    """Main CLI entry point."""
    config = parse_config()

    if not os.path.exists(config["src_dir"]):
        print(f"ERROR: Source dir '{config['src_dir']}' not found.", file=sys.stderr)
        sys.exit(1)
        return
    # A dry run must not touch the filesystem, so the destination is only
    # created when files will actually be moved.
    if not config["dry_run"]:
        os.makedirs(config["dst_dir"], exist_ok=True)
    all_dir = os.path.join(config["dst_dir"], "_all")

    # Maintenance flags are standalone operations: they run and exit so a
    # link fixup can never silently turn into a bulk file move.
    if config["cleanup_broken_links"] or config["backfill_all_links"]:
        maintenance_errors = 0
        if config["cleanup_broken_links"]:
            removed_count = cleanup_broken_symlinks(
                all_dir,
                config["dry_run"],
                config["debug"],
            )
            action = "Would remove" if config["dry_run"] else "Removed"
            print(f"{action} {removed_count} broken symlink(s) from {all_dir}")
        if config["backfill_all_links"]:
            backfilled_links, backfill_errors = backfill_all_symlinks(
                config["dst_dir"],
                config["dry_run"],
                config["debug"],
            )
            maintenance_errors += backfill_errors
            action = "Would create" if config["dry_run"] else "Created"
            print(f"{action} {backfilled_links} `_all` symlink(s) from existing sessions")
        if config["open_when_done"] and maintenance_errors == 0:
            open_destination_if_present(config["dst_dir"])
        sys.exit(1 if maintenance_errors else 0)
        return

    file_data = scan_files(config["src_dir"], debug=config["debug"])
    if not file_data:
        print(f"No image files found in {config['src_dir']}")
        if config["open_when_done"]:
            open_destination_if_present(config["dst_dir"])
        sys.exit(0)
        return

    batches = group_by_time(file_data, config["gap"])
    print(f"Found {len(batches)} batches (gap {config['gap'].total_seconds()/60:.0f} min, "
          f"sim threshold {config['sim_thresh']}, "
          f"cluster limit {config['cluster_size_limit'] or 'unlimited'}, "
          f"workers {config['workers']}).\n")

    session_count, total_files, move_errors = process_clusters(batches, config)
    print_summary(
        session_count,
        total_files,
        move_errors,
        config["dry_run"],
    )
    if config["open_when_done"] and move_errors == 0:
        open_destination_if_present(config["dst_dir"])


if __name__ == "__main__":
    main()
