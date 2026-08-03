# Contributing to slimv

Thanks for your interest in improving slimv! It's a small, focused toolkit that
drives ffmpeg to shrink video without visible quality loss — contributions that
keep it that way are very welcome.

## Development setup

```bash
git clone https://github.com/abdelhaleemahmed/slimv.git
cd slimv
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1   |  Linux/macOS: source .venv/bin/activate
pip install -e ".[test]"
```

You also need **ffmpeg/ffprobe** on your `PATH` to run the tool itself (not
needed for the unit tests). See the docs' *Requirements* section.

## Running the tests

```bash
pytest
```

The unit suite is **fast and ffmpeg-free** — it covers the deterministic logic
(duration parsing, the rename engine, profile invariants, the recommend decision
rule, the verify-filter regexes, the CLI parser). Please add tests for any new
logic, and keep ffmpeg/GPU/real-media out of the unit tests (those paths are
verified manually / by integration).

## Building the docs

```bash
cd docs && python -m sphinx -b html source _build/html
```

Docs are reStructuredText under `docs/source/`. Keep the build **warning-free**.

## File encoding (UTF-8)

Every source and docs file is **UTF-8**. This matters most on Windows: an editor that
saves as ANSI / Windows-1252 corrupts any non-ASCII character — an em-dash `—`, curly
quotes, arrows — into a stray byte that renders as `�`/`▒`. Sphinx's `-W` build can then
fail, or the text just looks wrong (e.g. a CHANGELOG heading whose `—` became a lone
`0x97` byte).

**Check** a file is valid UTF-8:

```bash
python -c "open('CHANGELOG.md', encoding='utf-8').read()" && echo OK
#  a UnicodeDecodeError instead of "OK" means it is NOT valid UTF-8
```

Scan the whole repo for offenders:

```bash
python - <<'EOF'
import pathlib
for p in pathlib.Path('.').rglob('*'):
    if p.is_file() and p.suffix in {'.md', '.rst', '.py', '.toml', '.yml'}:
        try:
            p.read_text(encoding='utf-8')
        except UnicodeDecodeError as e:
            print(p, '->', e)
EOF
```

**Fix / prevent in vim** — check and force the file's encoding, then save:

```vim
:set fileencoding?          " what this file will be written as (want: utf-8)
:set fileencoding=utf-8     " force UTF-8 on the next write
:w
```

Make it the default in your `~/.vimrc`:

```vim
set encoding=utf-8
set fileencoding=utf-8
```

To repair a single mangled line from the shell without a UTF-8 locale getting in the
way, rewrite it in a byte-literal locale — e.g. line 8:

```bash
LC_ALL=C sed -i '8s/.*/## [0.2.1] — 2026-08-03/' CHANGELOG.md
```

**Vim's temp files** — `foo~` (backup), `.foo.un~` (persistent undo), `*.swp` (swap) —
are `.gitignore`d; never commit them. They appear because vim writes them next to the
file you edit.

## Guidelines

- **slimv orchestrates ffmpeg; it never re-implements a codec.** New features
  build ffmpeg command lines and interpret the results.
- **Quality first, then size** — profiles keep resolution/framerate/pixel format.
- Match the surrounding style (naming, docstrings, comment density).
- Update the docs and `CHANGELOG.md` when you change behavior.

## Pull requests

1. Branch from `main`.
2. Make sure `pytest` passes and the docs build cleanly.
3. Describe what changed and why. Small, focused PRs are easiest to review.

## Releasing

slimv uses `MAJOR.MINOR.PATCH` versions. A release is done **by hand** — there is
no publish automation. Two GitHub Actions fire on every push to `main`: `ci.yml`
(tests + docs build) and `docs.yml` (deploy to GitHub Pages). The **git tag** is the
permanent marker for the version; tags themselves currently trigger no workflow.

Steps (worked example: releasing `0.2.1`):

1. **Start clean on `main`.** Everything for the release should be committed or ready
   to commit; nothing unrelated left dangling.

   ```bash
   git switch main && git pull --ff-only
   git status                       # know exactly what's staged/unstaged
   ```

2. **Bump the version in all three places** (they must agree):

   - `pyproject.toml`      → `version = "0.2.1"`
   - `slimv/__init__.py`   → `__version__ = "0.2.1"`
   - `docs/source/conf.py` → both `release = "0.2.1"` and `version = "0.2.1"`

   Confirm none were missed:

   ```bash
   grep -rn '0\.2\.0' pyproject.toml slimv/__init__.py docs/source/conf.py
   # (should print nothing once all are bumped)
   ```

3. **Update `CHANGELOG.md`** — rename the `## [Unreleased]` heading to
   `## [0.2.1] — YYYY-MM-DD` (today's date), and start a fresh empty `## [Unreleased]`
   above it for future work.

4. **Verify locally** before committing (same gates CI enforces):

   ```bash
   pytest -q
   python -m sphinx -b html docs/source docs/_build/html -W
   ```

5. **Commit** the bump:

   ```bash
   git add -A
   git commit -m "Release 0.2.1"
   ```

6. **Tag it** — annotated (`-a`) so the tag carries a message, date, and author (a
   plain lightweight tag stores none of that):

   ```bash
   git tag -a v0.2.1 -m "slimv 0.2.1"
   git tag                          # verify v0.2.1 is listed
   ```

7. **Push the commit and the tag.** `--follow-tags` sends annotated tags that point at
   commits being pushed, so branch and tag go together:

   ```bash
   git push origin main --follow-tags
   ```

   The push to `main` triggers `ci.yml` (tests + docs) and `docs.yml` (Pages deploy).
   Watch them: `gh run watch` or the repo's **Actions** tab.

8. **(Optional) GitHub Release** — turns the tag into a Release entry with notes:

   ```bash
   gh release create v0.2.1 --title "slimv 0.2.1" --notes-file - <<'EOF'
   (paste the 0.2.1 CHANGELOG section here)
   EOF
   ```

**Fixing a botched tag** (before others pull it): `git tag -d v0.2.1` deletes it
locally, `git push origin :refs/tags/v0.2.1` deletes it on the remote. Re-tag, re-push.

## Reporting bugs

Open an issue with your OS, Python version, `ffmpeg -version`, the exact command,
and the output. `slimv hwcheck` output helps for hardware-encoder issues.
