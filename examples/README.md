# Prompt Image Organizer Examples

This directory contains quick usage recipes for the current layout and CLI.

## Quick Start

```bash
# Preview organization
uv run prompt-image-organizer ./images ./image-sessions

# Move files and open the destination when done
uv run prompt-image-organizer ./images ./image-sessions -x --open
```

Resulting structure:

```text
./image-sessions/
  20260313/
    20260313-1103-session-002-054/
      63630146fe54c453e9d4ad0d98d0a5de.png
  _all/
    63630146fe54c453e9d4ad0d98d0a5de.png -> ../20260313/20260313-1103-session-002-054/63630146fe54c453e9d4ad0d98d0a5de.png
```

## Real-World Recipes

### Organize a large dump with debug output

```bash
uv run prompt-image-organizer ./dump ./image-sessions --debug -x
```

### Use a larger time gap

```bash
uv run prompt-image-organizer ./dump ./image-sessions --gap 1440 --sim 0.5 -x
```

### Limit oversized sessions

```bash
uv run prompt-image-organizer ./dump ./image-sessions --limit 100 -x
```

### Rebuild missing `_all` links

```bash
uv run prompt-image-organizer ./images ./image-sessions --backfill-all-links -x
```

### Remove broken `_all` links

```bash
uv run prompt-image-organizer ./images ./image-sessions --cleanup-broken-links -x
```

## Notes

- Without `-x`, the tool performs a dry run.
- Default session folder names are neutral: `YYYYMMDD-HHMM-session-<cluster>-<count>`.
- Moved files are renamed to MD5-based filenames plus their original extension.
- `_all/` contains symlinks, not copies.
