"""Core functionality for prompt image organizer."""

import os
import shutil
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict, Any, Optional

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None  # We'll handle this gracefully.


def get_env_int(name: str, default: int) -> int:
    """Get integer from environment variable with fallback to default.

    Args:
        name: Environment variable name
        default: Default value if environment variable is not set or invalid

    Returns:
        Integer value from environment or default
    """
    try:
        return int(os.environ.get(name, default))
    except Exception:
        return default


def get_env_float(name: str, default: float) -> float:
    """Get float from environment variable with fallback to default.

    Args:
        name: Environment variable name
        default: Default value if environment variable is not set or invalid

    Returns:
        Float value from environment or default
    """
    try:
        return float(os.environ.get(name, default))
    except Exception:
        return default


def sanitize_for_folder(name: str) -> str:
    """Sanitize a string for use as a folder name.

    Args:
        name: Original string to sanitize

    Returns:
        Sanitized string suitable for folder names (lowercase, dashes, max 30 chars)
    """
    # Replace underscores with dashes
    s = re.sub(r'[_]+', '-', name)
    # Replace non-alphanumeric, non-dash, non-dot chars with dash
    s = re.sub(r'[^a-zA-Z0-9\-\.]', '-', s)
    # Collapse multiple dashes
    s = re.sub(r'-+', '-', s)
    # Strip leading/trailing dashes/underscores
    s = s.strip('-_').lower()
    # Truncate to 30 chars and strip trailing dashes again
    return s[:30].rstrip('-')


def get_image_files(src_dir: str) -> List[str]:
    """Get list of image files from source directory.

    Args:
        src_dir: Source directory path

    Returns:
        List of image filenames (sorted)
    """
    return sorted([
        f for f in os.listdir(src_dir)
        if os.path.isfile(os.path.join(src_dir, f)) and
        f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
    ])


def extract_prompt(filename: str) -> str:
    """Extract prompt from filename by removing numbering suffixes.

    Args:
        filename: Image filename

    Returns:
        Extracted prompt string
    """
    base = os.path.splitext(filename)[0]
    prompt = re.sub(r'(_\d+)+$', '', base)
    return prompt


def similar(a: str, b: str, threshold: float = 0.8) -> bool:
    """Check if two strings are similar using SequenceMatcher.

    Args:
        a: First string
        b: Second string
        threshold: Similarity threshold (0-1)

    Returns:
        True if strings are similar above threshold
    """
    return SequenceMatcher(None, a, b).ratio() >= threshold


def group_by_time(file_data: List[Tuple[str, datetime, str]], gap: timedelta) -> List[List[Tuple[str, datetime, str]]]:
    """Group files by time gaps.

    Args:
        file_data: List of (filename, mtime, prompt) tuples
        gap: Time gap threshold for grouping

    Returns:
        List of batches, each containing file data tuples
    """
    batches = []
    current_batch = []
    last_time = None
    for item in file_data:
        f, mtime, prompt = item
        if not current_batch:
            current_batch.append(item)
        else:
            if (mtime - last_time) > gap:
                batches.append(current_batch)
                current_batch = []
            current_batch.append(item)
        last_time = mtime
    if current_batch:
        batches.append(current_batch)
    return batches


def cluster_prompts(batch: List[Tuple[str, datetime, str]], threshold: float = 0.8, cluster_size_limit: Optional[int] = None) -> List[List[Tuple[str, datetime, str]]]:
    """Cluster files by prompt similarity.

    Args:
        batch: List of (filename, mtime, prompt) tuples
        threshold: Similarity threshold for clustering
        cluster_size_limit: Maximum size for each cluster (None for unlimited)

    Returns:
        List of clusters, each containing file data tuples
    """
    clusters = []
    for f, mtime, prompt in batch:
        placed = False
        for cluster in clusters:
            if similar(prompt, cluster[0][2], threshold):
                if not cluster_size_limit or len(cluster) < cluster_size_limit:
                    cluster.append((f, mtime, prompt))
                    placed = True
                    break
        if not placed:
            clusters.append([(f, mtime, prompt)])
    return clusters


def find_unique_folder_name(dst_dir: str, base_folder_name: str) -> str:
    """Find a unique folder name by appending numbers if needed.

    Args:
        dst_dir: Destination directory
        base_folder_name: Base folder name

    Returns:
        Unique folder name
    """
    folder_name = base_folder_name
    counter = 1
    while os.path.exists(os.path.join(dst_dir, folder_name)):
        folder_name = f"{base_folder_name}_{counter}"
        counter += 1
    return folder_name


def move_file_worker(src: str, dst: str, session_folder: str, dry_run: bool) -> Tuple[str, str, bool, Optional[str]]:
    """Thread worker for moving a file.

    Args:
        src: Source file path
        dst: Destination file path
        session_folder: Session folder path
        dry_run: If True, don't actually move files

    Returns:
        Tuple of (src, dst, success, error_message_or_None)
    """
    if dry_run:
        return (src, dst, True, None)
    try:
        os.makedirs(session_folder, exist_ok=True)
        shutil.move(src, dst)
        return (src, dst, True, None)
    except Exception as e:
        return (src, dst, False, str(e))


def scan_files(src_dir: str) -> List[Tuple[str, datetime, str]]:
    """Scan source directory for image files and extract metadata.

    Args:
        src_dir: Source directory path

    Returns:
        List of (filename, mtime, prompt) tuples sorted by modification time
    """
    files = get_image_files(src_dir)
    file_data = []
    for f in files:
        path = os.path.join(src_dir, f)
        mtime = datetime.fromtimestamp(os.path.getmtime(path))
        prompt = extract_prompt(f)
        file_data.append((f, mtime, prompt))
    file_data.sort(key=lambda x: x[1])
    return file_data


def process_clusters(batches: List[List[Tuple[str, datetime, str]]], config: Dict[str, Any]) -> Tuple[int, int, int]:
    """Process file clusters and move files to session folders.

    Args:
        batches: List of file batches
        config: Configuration dictionary

    Returns:
        Tuple of (session_count, total_files, move_errors)
    """
    session_count = 0
    total_files = 0
    move_errors = 0

    for batch in batches:
        clusters = cluster_prompts(
            batch,
            threshold=config["sim_thresh"],
            cluster_size_limit=config["cluster_size_limit"]
        )
        for cluster in clusters:
            first_file, mtime, prompt = cluster[0]
            date_str = mtime.strftime('%Y%m%d_%H%M')
            base_folder_name = f"session_{date_str}_{sanitize_for_folder(prompt)}"
            folder_name = find_unique_folder_name(config["dst_dir"], base_folder_name)
            session_folder = os.path.join(config["dst_dir"], folder_name)

            print(f"\nSession {session_count+1}: {session_folder}")
            file_ops = []
            for f, _, _ in cluster:
                src = os.path.join(config["src_dir"], f)
                dst = os.path.join(session_folder, f)
                file_ops.append((src, dst, session_folder, config["dry_run"]))
            results = []

            if tqdm and len(file_ops) > 2:
                bar = tqdm(total=len(file_ops), desc="Moving" if not config["dry_run"] else "Preview", ncols=80)
            else:
                bar = None

            with ThreadPoolExecutor(max_workers=config["workers"]) as executor:
                futures = [executor.submit(move_file_worker, *op) for op in file_ops]
                for fut in as_completed(futures):
                    src, dst, success, err = fut.result()
                    results.append((src, dst, success, err))
                    if bar: bar.update(1)
                    if not success:
                        move_errors += 1
                        print(f"    ERROR: Could not move {src} to {dst}: {err}")
            if bar: bar.close()

            # Log each operation (so output appears in order for small clusters)
            if not tqdm or len(file_ops) <= 2:
                for src, dst, success, err in results:
                    print(f"  {'MOVE' if not config['dry_run'] else 'WOULD MOVE'} {src} -> {dst}")

            session_count += 1
            total_files += len(cluster)
    return session_count, total_files, move_errors


def print_summary(session_count: int, total_files: int, move_errors: int, dry_run: bool) -> None:
    """Print summary of processing results.

    Args:
        session_count: Number of sessions created
        total_files: Total number of files processed
        move_errors: Number of file move errors
        dry_run: Whether this was a dry run
    """
    print("\n=== SUMMARY ===")
    print(f"Total sessions: {session_count}")
    print(f"Total files {'to be moved' if dry_run else 'moved'}: {total_files}")
    if move_errors:
        print(f"Total errors during file move: {move_errors}")