"""Core functionality for prompt image organizer."""

import base64
import hashlib
import os
import re
import shutil
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None  # We'll handle this gracefully.


STOPWORDS: set[str] = {
    "a",
    "an",
    "and",
    "at",
    "be",
    "by",
    "for",
    "in",
    "of",
    "on",
    "the",
    "to",
    "with",
}

DEFAULT_FOLDER_PATTERN = "{datetime}-{slug}{checksum_suffix}-{count_padded}"


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
    """Create a compact slug suitable for folder names.

    Args:
        name: Original string to sanitize.

    Returns:
        Lowercase slug composed of up to three meaningful tokens joined with
        hyphens and trimmed to 18 characters.
    """
    tokens = re.findall(r"[A-Za-z0-9]+", name.lower())
    filtered_tokens = [token for token in tokens if token not in STOPWORDS]
    selected_tokens = filtered_tokens or tokens

    if not selected_tokens:
        return ""

    selected_tokens = selected_tokens[:3]
    slug = "-".join(selected_tokens)
    max_length = 18

    while len(slug) > max_length and len(selected_tokens) > 1:
        selected_tokens = selected_tokens[:-1]
        slug = "-".join(selected_tokens)

    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")

    return slug


def prompt_checksum(prompt: str, attempt: int = 0) -> str:
    """Return a short, base32 checksum for the given prompt."""
    salt = f"{prompt}-{attempt}" if attempt else prompt
    digest = hashlib.blake2b(salt.encode("utf-8"), digest_size=3).digest()
    encoded = base64.b32encode(digest).decode("ascii").rstrip("=").lower()
    return encoded[:3]


def build_folder_name(pattern: str, values: Dict[str, Any]) -> str:
    """Format the session folder name using the provided pattern and values.

    Args:
        pattern: Folder naming pattern using str.format placeholders.
        values: Mapping of placeholder names to substitution values.

    Returns:
        Formatted folder name string.

    Raises:
        ValueError: If the pattern references unknown placeholders or has
            invalid formatting directives.
    """
    try:
        folder_name = pattern.format(**values)
    except KeyError as exc:
        missing = exc.args[0]
        raise ValueError(
            f"Unknown placeholder '{missing}' in folder pattern '{pattern}'."
        ) from exc
    except ValueError as exc:
        raise ValueError(
            f"Invalid folder pattern '{pattern}': {exc}"
        ) from exc

    folder_name = folder_name.strip()
    if not folder_name:
        raise ValueError("Folder pattern produced an empty name.")

    if os.path.isabs(folder_name):
        raise ValueError("Folder pattern must not produce an absolute path.")

    if os.sep in folder_name or (os.altsep and os.altsep in folder_name):
        raise ValueError(
            "Folder pattern must produce a single folder name without path separators."
        )

    path_parts = pathlib_split(folder_name)
    if any(part == ".." for part in path_parts):
        raise ValueError("Folder pattern must not contain parent directory segments.")

    return folder_name


def pathlib_split(path: str) -> List[str]:
    """Split a relative path into normalized components."""
    normalized = os.path.normpath(path)
    if normalized == ".":
        return []
    return normalized.split(os.sep)


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


def validate_session_folder_path(dst_dir: str, folder_name: str) -> str:
    """Validate that a folder name resolves under the destination directory."""
    destination_root = os.path.abspath(dst_dir)
    session_folder = os.path.abspath(os.path.join(destination_root, folder_name))

    if os.path.commonpath([destination_root, session_folder]) != destination_root:
        raise ValueError(
            "Folder pattern must resolve within the destination directory."
        )

    return session_folder


def find_unique_file_name(
    dst_dir: str,
    base_file_name: str,
    reserved_names: Optional[set[str]] = None,
) -> str:
    """Find a unique file name by appending numeric suffixes when required."""
    reserved_names = reserved_names or set()
    if (
        base_file_name not in reserved_names
        and not os.path.lexists(os.path.join(dst_dir, base_file_name))
    ):
        return base_file_name

    stem, extension = os.path.splitext(base_file_name)
    counter = 2
    while True:
        candidate = f"{stem}-{counter:02d}{extension}"
        if (
            candidate not in reserved_names
            and not os.path.lexists(os.path.join(dst_dir, candidate))
        ):
            return candidate
        counter += 1


def create_symlink(
    target_path: str,
    symlink_dir: str,
    link_name: str,
    dry_run: bool,
) -> Tuple[str, bool, Optional[str]]:
    """Create a symlink inside the aggregate directory."""
    link_path = os.path.join(symlink_dir, link_name)
    if dry_run:
        return (link_path, True, None)

    try:
        os.makedirs(symlink_dir, exist_ok=True)
        relative_target = os.path.relpath(target_path, symlink_dir)
        os.symlink(relative_target, link_path)
        return (link_path, True, None)
    except Exception as exc:
        return (link_path, False, str(exc))


def find_unique_folder_name(
    dst_dir: str,
    base_folder_name: str,
    reserved_names: Optional[set[str]] = None,
) -> str:
    """Find a unique folder name by appending numeric suffixes when required.

    Args:
        dst_dir: Destination directory.
        base_folder_name: Preferred folder name.

    Returns:
        Folder name that does not exist on disk.
    """
    reserved_names = reserved_names or set()
    if (
        base_folder_name not in reserved_names
        and not os.path.exists(os.path.join(dst_dir, base_folder_name))
    ):
        return base_folder_name

    counter = 2
    while True:
        candidate = f"{base_folder_name}-{counter:02d}"
        if (
            candidate not in reserved_names
            and not os.path.exists(os.path.join(dst_dir, candidate))
        ):
            return candidate
        counter += 1


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
    base_slug_tracker: Dict[str, set[str]] = defaultdict(set)
    slug_tracker: Dict[str, set[str]] = defaultdict(set)
    reserved_folder_names: Dict[str, set[str]] = defaultdict(set)
    reserved_link_names: set[str] = set()
    folder_pattern = config.get("folder_pattern", DEFAULT_FOLDER_PATTERN)
    all_dir = os.path.join(config["dst_dir"], "_all")

    # Calculate total files across all batches for progress tracking
    total_files_to_process = sum(len(cluster) for batch in batches
                                for cluster in cluster_prompts(batch, threshold=config["sim_thresh"], cluster_size_limit=config["cluster_size_limit"]))

    # Initialize total progress bar if tqdm is available
    if tqdm and total_files_to_process > 2:
        total_bar = tqdm(
            total=total_files_to_process,
            desc="Processing files" if not config["dry_run"] else "Previewing files",
            ncols=120,  # Wider progress bar
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} files [{elapsed}<{remaining}, {rate_fmt}]',
            dynamic_ncols=True  # Allow dynamic resizing
        )
    else:
        total_bar = None

    for batch_idx, batch in enumerate(batches):
        clusters = cluster_prompts(
            batch,
            threshold=config["sim_thresh"],
            cluster_size_limit=config["cluster_size_limit"]
        )

        for cluster_idx, cluster in enumerate(clusters):
            first_file, mtime, prompt = cluster[0]
            timestamp = mtime.strftime("%Y%m%d-%H%M")

            base_slug = sanitize_for_folder(prompt) or "prompt"
            base_slugs = base_slug_tracker[timestamp]
            slugs_in_use = slug_tracker[timestamp]

            checksum = ""
            if base_slug in base_slugs:
                attempt = 0
                while True:
                    checksum_candidate = prompt_checksum(prompt, attempt)
                    candidate_slug = f"{base_slug}-{checksum_candidate}"
                    if candidate_slug not in slugs_in_use:
                        slug = candidate_slug
                        checksum = checksum_candidate
                        break
                    attempt += 1
            else:
                base_slugs.add(base_slug)
                slug = base_slug

            slugs_in_use.add(slug)

            folder_values = {
                "date": mtime.strftime("%Y%m%d"),
                "time": mtime.strftime("%H%M"),
                "datetime": timestamp,
                "slug": slug,
                "base_slug": base_slug,
                "count": len(cluster),
                "count_padded": f"{len(cluster):03d}",
                "cluster_index": cluster_idx + 1,
                "batch_index": batch_idx + 1,
                "checksum": checksum,
                "checksum_suffix": f"-{checksum}" if checksum else "",
            }

            try:
                base_folder_name = build_folder_name(folder_pattern, folder_values)
            except ValueError as exc:
                raise ValueError(f"Failed to build folder name: {exc}") from exc

            date_folder = os.path.join(config["dst_dir"], folder_values["date"])
            date_reserved_names = reserved_folder_names[date_folder]
            folder_name = find_unique_folder_name(
                date_folder,
                base_folder_name,
                date_reserved_names,
            )
            date_reserved_names.add(folder_name)
            session_folder = validate_session_folder_path(
                date_folder, folder_name
            )

            # Print session info if debug mode is enabled
            if config.get("debug", False):
                print(f"\nSession {session_count+1}: {session_folder}")

            file_ops = []
            for f, _, _ in cluster:
                src = os.path.join(config["src_dir"], f)
                dst = os.path.join(session_folder, f)
                file_ops.append((src, dst, session_folder, config["dry_run"]))

            results = []

            with ThreadPoolExecutor(max_workers=config["workers"]) as executor:
                futures = [executor.submit(move_file_worker, *op) for op in file_ops]

                for fut in as_completed(futures):
                    src, dst, success, err = fut.result()
                    results.append((src, dst, success, err))
                    if total_bar:
                        total_bar.update(1)
                        # Update description to show current file being processed
                        filename = os.path.basename(src)
                        # Show more of the filename for better visibility
                        display_name = filename[:40] + "..." if len(filename) > 40 else filename
                        total_bar.set_postfix(file=display_name)
                    if not success:
                        move_errors += 1
                        # Always print errors
                        print(f"    ERROR: Could not move {src} to {dst}: {err}")

            for _, dst, success, _ in results:
                if not success:
                    continue

                link_name = find_unique_file_name(
                    all_dir,
                    os.path.basename(dst),
                    reserved_link_names,
                )
                reserved_link_names.add(link_name)
                link_path, link_success, link_error = create_symlink(
                    dst,
                    all_dir,
                    link_name,
                    config["dry_run"],
                )
                if not link_success:
                    move_errors += 1
                    print(
                        f"    ERROR: Could not create symlink {link_path} -> {dst}: {link_error}"
                    )

            # Log each operation if debug mode is enabled
            if config.get("debug", False):
                for src, dst, success, err in results:
                    print(f"  {'MOVE' if not config['dry_run'] else 'WOULD MOVE'} {src} -> {dst}")

            session_count += 1
            total_files += len(cluster)

    if total_bar: total_bar.close()
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
