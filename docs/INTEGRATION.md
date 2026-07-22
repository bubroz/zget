# zget integration guide (librarian · Chimera · agents)

How other projects should call zget after the 2026-07 path, doctor, and C-SPAN work.

## Library location

Never hardcode `~/Downloads/zget`. Resolve the library root in this order:

1. **`ZGET_HOME`** environment variable  
2. **`~/.config/zget/config.json`** → key `zget_home`  
3. Fallback: `~/Downloads/zget` (zget default only)

Python helper (librarian): `librarian.utils.zget_paths.default_zget_home()`.

```bash
# Confirm where media will land
cd ~/Projects/zget && uv run zget --stats
cd ~/Projects/zget && uv run zget config show
```

Layout under the home:

```text
$ZGET_HOME/
  library.db
  videos/<platform>/   # youtube, c-span, …
  thumbnails/
  exports/
  logs/
```

## Capture (always zget, never raw yt-dlp)

```bash
cd ~/Projects/zget
uv run zget "<URL>" --quiet
uv run zget "<URL>" -o /path/to/dir --flat   # pipeline drop; still prefer default home when possible
uv run zget info "<URL>" --json --compact    # metadata only
uv run zget list-channel "<channel-url>" --since 2020-01-01 --jsonl
```

## C-SPAN

| URL shape | Support |
|-----------|---------|
| `c-span.org/video/?…` | Native yt-dlp (unchanged) |
| `c-span.org/program/.../{id}` | **Supported** — resolves public HLS + Referer headers (`src/zget/platforms/cspan.py`) |

```bash
uv run zget info 'https://www.c-span.org/program/.../NNNNN'
uv run zget 'https://www.c-span.org/program/.../NNNNN' --quiet
```

No separate recover script is required for free public program streams.

## Path health (doctor)

```bash
uv run zget --doctor                 # classify only
uv run zget paths check              # same taxonomy
uv run zget --doctor --fix           # rewrite stale home paths only (safe)
uv run zget paths rewrite --dry-run  # preview migration after moving ZGET_HOME
# DANGEROUS — only after reviewing true orphans:
uv run zget --doctor --fix --purge-orphans
```

### Path classes

| Class | Meaning | Purge? |
|-------|---------|--------|
| **healthy** | File exists at stored path under `ZGET_HOME` | No |
| **relocatable** | Stale absolute home; file found under current `ZGET_HOME` | No — use `--fix` / `paths rewrite` |
| **off-home** | File exists outside `ZGET_HOME` (pipeline `-o`) | No |
| **offline volume** | Path under `/Volumes/X/...` and `X` is not mounted | **Never** until remount + re-check |
| **orphan** | File missing and (if volume path) the volume root is present | Only with explicit `--purge-orphans` |

After moving the library, always run `paths rewrite` (or `doctor --fix`) before trusting orphan counts.

## Agent / skill contract

- Invoke: `cd ~/Projects/zget && uv run zget "URL" --quiet`  
- Report the path **zget prints** or from `--stats` / search — do not guess Downloads  
- Librarian ingest defaults follow the same home resolution  
- Chimera A/V collection should use `zget` for program and video URLs alike  

## Public vs operator notes

- **Public zget repo:** generic docs only (this file, README, AGENTS)  
- **Operator machine paths** (volume names): private skills / `~/.grok/operator-os/zget-OPERATOR.md` only  
