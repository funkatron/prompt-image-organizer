# 2026-08-04 - Usability overhaul (0.2.0)

## TL;DR

A humane-interface review (Jef Raskin lens: user data is sacred, no
irreversible actions, visible system state) found that the tool destroyed the
prompt embedded in original filenames with no undo, hid the dry-run plan
behind `--debug`, and mutated the filesystem during "previews". All findings
were fixed across seven commits and released as 0.2.0.

## What changed (one commit each)

1. `38c0f85` - Per-session `manifest.json`: original name, extracted prompt,
   mtime, stored hash name. Makes moves auditable and reversible.
2. `ba153f6` - Default dry-run output now prints the plan (session folders +
   sample original filenames); progress bar removed from dry runs; summary
   hints how to apply.
3. `004f3d6` - Dry runs are truly read-only: no destination `makedirs`, no
   MD5 hashing (placeholder `<md5>` names), `--open` copes with a missing
   destination, backfill tolerates a missing destination.
4. `93d6e74` - `--move` added as the primary spelling of `-x`; explicit
   `--dry-run` flag; the two conflict loudly.
5. `ff430f0` - New `{session_index}` placeholder (run-global, never repeats);
   default pattern is now `{datetime}-session-{session_index:03d}-x{count_padded}`
   so the file count no longer reads as an ordinal.
6. `1abb23c` - `--cleanup-broken-links` / `--backfill-all-links` are
   standalone: they run and exit, never organizing the source as a side
   effect. Counts are reported even when zero.
7. `09b3c51` - Polish: fatal errors to stderr, argparse errors point at `-h`,
   invalid env values warn instead of silently defaulting, help documents the
   top-level-only scan, dead tqdm hint removed.
8. `281deef` - Docs (README/CHANGELOG/AGENTS.md), `pio` short CLI alias,
   version bump to 0.2.0 (uv.lock caught up from a stale 1.2.0 entry).

## Testing

- Behavior-focused tests added for each change (81 passed, 2 skipped).
- Notable tests: manifest round-trip covers every moved file; dry run proven
  not to create the destination and not to read file contents (unreadable
  file still previews); maintenance flag proven not to move source images;
  session numbers proven unique across batches.
- Manual end-to-end verification with throwaway data in /tmp: dry-run plan,
  real move, manifest contents, `pio` alias.

## Decisions and notes

- Kept the `sys.exit(...); return` pattern in `cli.main` - tests patch
  `sys.exit`, so the `return` prevents fall-through. Not dead code.
- Chose a `pio` alias over a full project rename: non-breaking, keeps the
  descriptive package name for PyPI.
- Not implemented (future candidates): an `--undo` command replaying
  manifests in reverse; recursive source scanning; duplicate-content
  detection beyond the `-02` suffix.
