"""Core functionality for prompt image organizer."""

import base64
import hashlib
import json
import os
import re
import shutil
import sys
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

DEFAULT_FOLDER_PATTERN = "{datetime}-session-{session_index:03d}-x{count_padded}"

MANIFEST_FILE_NAME = "manifest.json"
MANIFEST_VERSION = 1

# How many original filenames to list per session in the dry-run plan.
PLAN_SAMPLE_LIMIT = 5


def write_session_manifest(
    session_folder: str,
    source_dir: str,
    entries: List[Dict[str, str]],
) -> Optional[str]:
    """Write a manifest recording original names for the moved files.

    The manifest is what makes a move reversible and auditable: the original
    filename carries the prompt, which is otherwise lost when files are
    renamed to content hashes.

    Args:
        session_folder: Session folder the files were moved into.
        source_dir: Directory the files were moved from.
        entries: One mapping per file with keys ``original_name``, ``prompt``,
            ``modified_at``, and ``stored_name``.

    Returns:
        Error message on failure, otherwise None.
    """
    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_dir": os.path.abspath(source_dir),
        "files": sorted(entries, key=lambda entry: entry["original_name"]),
    }
    manifest_path = os.path.join(session_folder, MANIFEST_FILE_NAME)
    try:
        os.makedirs(session_folder, exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    except Exception as exc:
        return str(exc)
    return None


def find_session_manifests(dst_dir: str) -> List[str]:
    """Return manifest paths under dated session folders, sorted."""
    if not os.path.isdir(dst_dir):
        return []

    manifest_paths: List[str] = []
    for date_entry in sorted(os.listdir(dst_dir)):
        if date_entry == "_all":
            continue
        date_dir = os.path.join(dst_dir, date_entry)
        if not os.path.isdir(date_dir):
            continue
        if not re.fullmatch(r"\d{8}", date_entry):
            continue
        for session_entry in sorted(os.listdir(date_dir)):
            session_dir = os.path.join(date_dir, session_entry)
            if not os.path.isdir(session_dir):
                continue
            manifest_path = os.path.join(session_dir, MANIFEST_FILE_NAME)
            if os.path.isfile(manifest_path):
                manifest_paths.append(manifest_path)
    return manifest_paths


def load_session_manifest(manifest_path: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Load and validate a session manifest file."""
    try:
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except Exception as exc:
        return None, str(exc)

    if manifest.get("manifest_version") != MANIFEST_VERSION:
        return None, "unsupported manifest_version"

    source_dir = manifest.get("source_dir")
    if not source_dir or not isinstance(source_dir, str):
        return None, "missing source_dir"

    files = manifest.get("files")
    if not isinstance(files, list):
        return None, "missing files list"

    for entry in files:
        if not isinstance(entry, dict):
            return None, "invalid file entry"
        for key in ("original_name", "prompt", "modified_at", "stored_name"):
            if key not in entry or not isinstance(entry[key], str):
                return None, f"file entry missing {key}"

    return manifest, None


def remove_symlinks_to_target(
    all_dir: str,
    target_path: str,
    dry_run: bool,
    debug: bool = False,
) -> int:
    """Remove aggregate symlinks that resolve to the given target path."""
    if not os.path.isdir(all_dir):
        return 0

    resolved_target = os.path.realpath(target_path)
    removed_count = 0
    for entry in sorted(os.listdir(all_dir)):
        link_path = os.path.join(all_dir, entry)
        if not os.path.islink(link_path):
            continue
        if os.path.realpath(link_path) != resolved_target:
            continue
        removed_count += 1
        if debug:
            action = "REMOVE LINK" if not dry_run else "WOULD REMOVE LINK"
            print(f"  {action} {link_path}")
        if not dry_run:
            os.unlink(link_path)
    return removed_count


def restore_file_worker(
    src: str,
    dst: str,
    modified_at: Optional[str],
    dry_run: bool,
) -> Tuple[str, str, bool, Optional[str]]:
    """Move a file back to its original name and optionally restore mtime."""
    if dry_run:
        return (src, dst, True, None)
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        if modified_at:
            timestamp = datetime.fromisoformat(modified_at).timestamp()
            os.utime(dst, (timestamp, timestamp))
        return (src, dst, True, None)
    except Exception as exc:
        return (src, dst, False, str(exc))


def undo_from_manifests(
    dst_dir: str,
    dry_run: bool,
    debug: bool = False,
    workers: int = 8,
) -> Tuple[int, int, int]:
    """Restore files recorded in session manifests back to their source dirs.

    Each manifest's ``source_dir`` is the restore destination. After a
    successful restore, matching ``_all`` symlinks are removed and empty
    session folders (plus their manifest) are cleaned up.

    Returns:
        Tuple of (session_count, total_files, restore_errors).
    """
    manifest_paths = find_session_manifests(dst_dir)
    if not manifest_paths:
        return (0, 0, 0)

    all_dir = os.path.join(dst_dir, "_all")
    session_count = 0
    total_files = 0
    restore_errors = 0

    if dry_run:
        print("Dry run - planned undo (no files will be restored):\n")

    for manifest_path in manifest_paths:
        manifest, error = load_session_manifest(manifest_path)
        if error:
            restore_errors += 1
            print(f"    ERROR: Could not read {manifest_path}: {error}")
            continue

        session_folder = os.path.dirname(manifest_path)
        restore_dir = manifest["source_dir"]
        relative_session = os.path.relpath(
            session_folder, os.path.abspath(dst_dir)
        )
        entries = manifest["files"]

        if dry_run:
            file_word = "file" if len(entries) == 1 else "files"
            print(f"  {relative_session}  ({len(entries)} {file_word} -> {restore_dir})")
            for entry in entries[:PLAN_SAMPLE_LIMIT]:
                print(
                    f"    {entry['stored_name']} -> {entry['original_name']}"
                )
            overflow = len(entries) - PLAN_SAMPLE_LIMIT
            if overflow > 0:
                print(f"    ... and {overflow} more")
            session_count += 1
            total_files += len(entries)
            continue

        file_ops = []
        for entry in entries:
            src = os.path.join(session_folder, entry["stored_name"])
            dst = os.path.join(restore_dir, entry["original_name"])
            if not os.path.isfile(src):
                restore_errors += 1
                print(f"    ERROR: Stored file missing for undo: {src}")
                continue
            if os.path.exists(dst):
                restore_errors += 1
                print(
                    f"    ERROR: Restore target already exists: {dst}"
                )
                continue
            file_ops.append(
                (src, dst, entry.get("modified_at"), dry_run)
            )

        results = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(restore_file_worker, *op) for op in file_ops
            ]
            for fut in as_completed(futures):
                src, dst, success, err = fut.result()
                results.append((src, dst, success, err))
                if not success:
                    restore_errors += 1
                    print(f"    ERROR: Could not restore {src} to {dst}: {err}")

        restored_sources = []
        for src, dst, success, _ in results:
            if not success:
                continue
            restored_sources.append(src)
            remove_symlinks_to_target(all_dir, dst, dry_run=False, debug=debug)
            total_files += 1
            if debug:
                print(f"  RESTORE {src} -> {dst}")

        if restored_sources and len(restored_sources) == len(file_ops):
            try:
                os.remove(manifest_path)
                os.rmdir(session_folder)
                if debug:
                    print(f"  REMOVED empty session {session_folder}")
            except OSError as exc:
                restore_errors += 1
                print(
                    f"    ERROR: Could not remove session folder {session_folder}: {exc}"
                )

        if restored_sources:
            session_count += 1

    return session_count, total_files, restore_errors


def print_undo_summary(
    session_count: int,
    total_files: int,
    restore_errors: int,
    dry_run: bool,
) -> None:
    """Print summary of undo results."""
    print("\n=== UNDO SUMMARY ===")
    print(f"Total sessions: {session_count}")
    print(f"Total files {'to be restored' if dry_run else 'restored'}: {total_files}")
    if restore_errors:
        print(f"Total errors during restore: {restore_errors}")
    if dry_run and session_count:
        print("This was a dry run; nothing was restored. Add --move (or -x) to apply.")


def get_env_int(name: str, default: int) -> int:
    """Get integer from environment variable with fallback to default.

    Invalid values fall back to the default with a warning, so a typo in
    the environment never silently changes behavior.

    Args:
        name: Environment variable name
        default: Default value if environment variable is not set or invalid

    Returns:
        Integer value from environment or default
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        print(
            f"WARNING: ignoring invalid {name}={raw!r}; using default {default}",
            file=sys.stderr,
        )
        return default


def get_env_float(name: str, default: float) -> float:
    """Get float from environment variable with fallback to default.

    Invalid values fall back to the default with a warning, so a typo in
    the environment never silently changes behavior.

    Args:
        name: Environment variable name
        default: Default value if environment variable is not set or invalid

    Returns:
        Float value from environment or default
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        print(
            f"WARNING: ignoring invalid {name}={raw!r}; using default {default}",
            file=sys.stderr,
        )
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


def compute_file_md5(path: str, chunk_size: int = 1024 * 1024) -> str:
    """Compute the MD5 digest for a file."""
    digest = hashlib.md5()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


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


def cleanup_broken_symlinks(
    symlink_dir: str,
    dry_run: bool,
    debug: bool = False,
) -> int:
    """Remove broken symlinks from the aggregate directory.

    Args:
        symlink_dir: Directory containing aggregate symlinks.
        dry_run: If True, report removals without mutating the filesystem.
        debug: If True, print each broken symlink encountered.

    Returns:
        Number of broken symlinks found.
    """
    if not os.path.isdir(symlink_dir):
        return 0

    removed_count = 0
    for entry in sorted(os.listdir(symlink_dir)):
        link_path = os.path.join(symlink_dir, entry)
        if not os.path.islink(link_path):
            continue
        if os.path.exists(link_path):
            continue

        removed_count += 1
        if debug:
            action = "REMOVE" if not dry_run else "WOULD REMOVE"
            print(f"  {action} broken symlink {link_path}")
        if not dry_run:
            os.unlink(link_path)

    return removed_count


def backfill_all_symlinks(
    dst_dir: str,
    dry_run: bool,
    debug: bool = False,
) -> Tuple[int, int]:
    """Populate `_all` symlinks from existing session folders.

    Args:
        dst_dir: Destination root containing dated session folders.
        dry_run: If True, report work without mutating the filesystem.
        debug: If True, print each symlink action.

    Returns:
        Tuple of (symlinks_created, symlink_errors).
    """
    if not os.path.isdir(dst_dir):
        return (0, 0)

    all_dir = os.path.join(dst_dir, "_all")
    reserved_link_names = {
        entry for entry in os.listdir(all_dir)
        if os.path.lexists(os.path.join(all_dir, entry))
    } if os.path.isdir(all_dir) else set()
    linked_targets = {
        os.path.realpath(os.path.join(all_dir, entry))
        for entry in reserved_link_names
        if os.path.islink(os.path.join(all_dir, entry))
        and os.path.exists(os.path.join(all_dir, entry))
    }

    created_count = 0
    error_count = 0

    for date_entry in sorted(os.listdir(dst_dir)):
        date_dir = os.path.join(dst_dir, date_entry)
        if date_entry == "_all" or not os.path.isdir(date_dir):
            continue
        if not re.fullmatch(r"\d{8}", date_entry):
            continue

        for session_entry in sorted(os.listdir(date_dir)):
            session_dir = os.path.join(date_dir, session_entry)
            if not os.path.isdir(session_dir):
                continue

            for image_name in get_image_files(session_dir):
                target_path = os.path.join(session_dir, image_name)
                resolved_target = os.path.realpath(target_path)
                if resolved_target in linked_targets:
                    if debug:
                        print(f"  SKIP existing symlink for {target_path}")
                    continue

                link_name = find_unique_file_name(
                    all_dir,
                    image_name,
                    reserved_link_names,
                )
                reserved_link_names.add(link_name)
                link_path, success, error = create_symlink(
                    target_path,
                    all_dir,
                    link_name,
                    dry_run,
                )
                if success:
                    created_count += 1
                    linked_targets.add(resolved_target)
                    if debug:
                        action = "LINK" if not dry_run else "WOULD LINK"
                        print(f"  {action} {link_path} -> {target_path}")
                    continue

                error_count += 1
                print(
                    f"    ERROR: Could not create symlink {link_path} -> {target_path}: {error}"
                )

    return created_count, error_count


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


def scan_files(
    src_dir: str,
    debug: bool = False,
    progress_every: int = 1000,
) -> List[Tuple[str, datetime, str]]:
    """Scan source directory for image files and extract metadata.

    Args:
        src_dir: Source directory path
        debug: If True, print periodic scan progress.
        progress_every: Number of files between progress updates.

    Returns:
        List of (filename, mtime, prompt) tuples sorted by modification time
    """
    if debug:
        print(f"Scanning image files in {src_dir}...")
    files = get_image_files(src_dir)
    if debug:
        print(f"Found {len(files)} candidate image file(s). Reading timestamps...")
    file_data = []
    for index, f in enumerate(files, start=1):
        path = os.path.join(src_dir, f)
        mtime = datetime.fromtimestamp(os.path.getmtime(path))
        prompt = extract_prompt(f)
        file_data.append((f, mtime, prompt))
        if debug and (
            index == len(files) or index % progress_every == 0
        ):
            print(f"  Scanned {index}/{len(files)} image file(s)")
    file_data.sort(key=lambda x: x[1])
    if debug:
        print("Finished scanning and sorting image files.")
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

    # A dry run prints the plan itself; a progress bar would only add noise.
    total_bar = None
    if tqdm and not config["dry_run"]:
        total_files_to_process = sum(
            len(cluster) for batch in batches
            for cluster in cluster_prompts(
                batch,
                threshold=config["sim_thresh"],
                cluster_size_limit=config["cluster_size_limit"],
            )
        )
        if total_files_to_process > 2:
            total_bar = tqdm(
                total=total_files_to_process,
                desc="Processing files",
                ncols=120,  # Wider progress bar
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} files [{elapsed}<{remaining}, {rate_fmt}]',
                dynamic_ncols=True  # Allow dynamic resizing
            )

    if config["dry_run"] and batches:
        print("Dry run - planned sessions (no files will be moved):\n")

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
                # Global counter: unlike cluster_index it never repeats
                # within a run, so default folder names stay unambiguous.
                "session_index": session_count + 1,
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

            if config["dry_run"]:
                relative_session = os.path.relpath(
                    session_folder, os.path.abspath(config["dst_dir"])
                )
                file_word = "file" if len(cluster) == 1 else "files"
                print(f"  {relative_session}  ({len(cluster)} {file_word})")
                for original_name, _, _ in cluster[:PLAN_SAMPLE_LIMIT]:
                    print(f"    {original_name}")
                overflow = len(cluster) - PLAN_SAMPLE_LIMIT
                if overflow > 0:
                    print(f"    ... and {overflow} more")

            # Print session info if debug mode is enabled
            if config.get("debug", False):
                print(f"\nSession {session_count+1}: {session_folder}")

            file_ops = []
            reserved_session_names: set[str] = set()
            source_metadata: Dict[str, Dict[str, str]] = {}
            for f, file_mtime, file_prompt in cluster:
                src = os.path.join(config["src_dir"], f)
                extension = os.path.splitext(f)[1].lower()
                if config["dry_run"]:
                    # Hashing reads every byte of every file; a preview
                    # should stay cheap, so show a placeholder instead.
                    target_name = f"<md5>{extension}"
                else:
                    hashed_name = f"{compute_file_md5(src)}{extension}"
                    target_name = find_unique_file_name(
                        session_folder,
                        hashed_name,
                        reserved_session_names,
                    )
                    reserved_session_names.add(target_name)
                dst = os.path.join(session_folder, target_name)
                source_metadata[src] = {
                    "original_name": f,
                    "prompt": file_prompt,
                    "modified_at": file_mtime.isoformat(timespec="seconds"),
                }
                file_ops.append((src, dst, session_folder, config["dry_run"]))

            if not config["dry_run"]:
                # Persist mappings before any moves so an interrupt (Ctrl-C,
                # kill) cannot leave renamed files without a recovery record.
                manifest_entries = []
                for src, dst, _, _ in file_ops:
                    entry = dict(source_metadata[src])
                    entry["stored_name"] = os.path.basename(dst)
                    manifest_entries.append(entry)
                manifest_error = write_session_manifest(
                    session_folder,
                    config["src_dir"],
                    manifest_entries,
                )
                if manifest_error:
                    move_errors += len(file_ops)
                    print(
                        f"    ERROR: Could not write manifest in {session_folder}: {manifest_error}"
                    )
                    session_count += 1
                    total_files += len(cluster)
                    continue

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
    if dry_run:
        print("This was a dry run; nothing was moved. Add --move (or -x) to apply.")
