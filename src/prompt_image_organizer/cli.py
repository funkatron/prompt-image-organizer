"""Command-line interface for prompt image organizer."""

import os
import sys
import argparse
from datetime import timedelta
from typing import Dict, Any

from .core import (
    get_env_int,
    get_env_float,
    scan_files,
    group_by_time,
    process_clusters,
    print_summary,
)


def print_help() -> None:
    """Print help message for the CLI."""
    print("""
Prompt Image Organizer

Usage:
  python3 -m prompt_image_organizer [SRC_DIR] [DST_DIR] [options]

Arguments:
  SRC_DIR           Source image directory (default: $SRC_DIR or current dir)
  DST_DIR           Destination session directory (default: $DST_DIR or ./sessions)

Options:
  --gap MIN         Max gap (minutes) to group into a batch/session [env: SESSION_GAP_MINUTES, default: 60]
  --sim F           Prompt similarity threshold [0-1, env: PROMPT_SIMILARITY, default: 0.8]
  --limit N         Maximum cluster (session) size [env: SESSION_CLUSTER_LIMIT, default: unlimited]
  --workers N       Number of concurrent file moves (default: 8)
  -x                Actually move files (default: dry run)
  -h, --help        Show this help message

Examples:
  python3 -m prompt_image_organizer ./imgs ./out --gap 45 --workers 12
  python3 -m prompt_image_organizer ./imgs ./out --sim 0.9 --limit 100 -x
  python3 -m prompt_image_organizer -h
""")


def parse_config() -> Dict[str, Any]:
    """Parse command line arguments and environment variables.

    Returns:
        Configuration dictionary
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('src', nargs='?', help="Source directory")
    parser.add_argument('dst', nargs='?', help="Destination directory")
    parser.add_argument('--gap', type=int, help="Gap in minutes (default 60)")
    parser.add_argument('--sim', type=float, help="Prompt similarity threshold (default 0.8)")
    parser.add_argument('--limit', type=int, help="Maximum session (cluster) size (default: unlimited)")
    parser.add_argument('--workers', type=int, help="Number of concurrent file moves (default: 8)")
    parser.add_argument('-x', action='store_true', help="Actually move files")
    parser.add_argument('-h', '--help', action='store_true', help="Show help")
    args = parser.parse_args()

    if args.help:
        print_help()
        sys.exit(0)

    src_dir = args.src or os.environ.get("SRC_DIR", ".")
    dst_dir = args.dst or os.environ.get("DST_DIR", "./sessions")
    gap_min = args.gap if args.gap is not None else get_env_int("SESSION_GAP_MINUTES", 60)
    sim_thresh = args.sim if args.sim is not None else get_env_float("PROMPT_SIMILARITY", 0.8)
    cluster_size_limit = args.limit if args.limit is not None else get_env_int("SESSION_CLUSTER_LIMIT", 0) or None
    dry_run = not args.x
    workers = args.workers if args.workers is not None else get_env_int("SESSION_WORKERS", 8)
    return {
        "src_dir": src_dir,
        "dst_dir": dst_dir,
        "gap": timedelta(minutes=gap_min),
        "sim_thresh": sim_thresh,
        "cluster_size_limit": cluster_size_limit,
        "dry_run": dry_run,
        "workers": workers
    }


def main() -> None:
    """Main CLI entry point."""
    config = parse_config()

    if not os.path.exists(config["src_dir"]):
        print(f"ERROR: Source dir '{config['src_dir']}' not found.")
        sys.exit(1)
    os.makedirs(config["dst_dir"], exist_ok=True)

    file_data = scan_files(config["src_dir"])
    if not file_data:
        print(f"No image files found in {config['src_dir']}")
        sys.exit(0)

    batches = group_by_time(file_data, config["gap"])
    print(f"Found {len(batches)} batches (gap {config['gap'].total_seconds()/60:.0f} min, "
          f"sim threshold {config['sim_thresh']}, "
          f"cluster limit {config['cluster_size_limit'] or 'unlimited'}, "
          f"workers {config['workers']}).\n")

    try:
        from tqdm import tqdm
        tqdm_available = True
    except ImportError:
        tqdm_available = False
        print("Note: tqdm not found; progress bars disabled. Install with 'pip install tqdm' for better UX.")

    session_count, total_files, move_errors = process_clusters(batches, config)
    print_summary(session_count, total_files, move_errors, config["dry_run"])


if __name__ == "__main__":
    main()