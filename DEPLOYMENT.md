# Deploying slimv to GitHub — step-by-step

The exact, repeatable process used to package slimv, publish it to GitHub, cut a
release with downloadable artifacts, and serve the landing page + docs on GitHub
Pages. Every step lists both the **command-line** way and the **manual (web UI)**
way. Substitute your own repo for `abdelhaleemahmed/slimv` and version for
`0.2.0` when reusing this for another tool.

- **One-time setup:** steps 0–9 (create the repo, first push, metadata, Pages).
- **Every release afterwards:** the short checklist at the end (§"Cutting a new release").

---

## 0. Prerequisites (install once)

| Tool | Why | Check |
|------|-----|-------|
| Python 3.9+ | build & test | `python --version` |
| `build` | builds the wheel/sdist | `pip install build` |
| `pytest` | run the tests | `pip install pytest` (or `pip install -e ".[test]"`) |
| Git | version control | `git --version` |
| GitHub CLI (`gh`) | create repo, release, Pages | `gh --version` |
| ffmpeg/ffprobe | to *run* slimv (not needed to build/test) | `ffmpeg -version` |

Authenticate the GitHub CLI once:

```bash
gh auth login          # choose GitHub.com → HTTPS → browser
gh auth status         # confirm you're logged in
```

> **Important — token scope.** Pushing GitHub Actions workflow files
> (`.github/workflows/*.yml`) requires the **`workflow`** scope. If you see
> *"refusing to allow an OAuth App to create or update workflow ... without
> `workflow` scope"* on push, run:
> ```bash
> gh auth refresh -h github.com -s workflow
> ```
> then push again.

---

## 1. Package files the repo needs

These live at the project root (already present in slimv):

| File | Purpose |
|------|---------|
| `pyproject.toml` | package metadata, dependencies, entry point, test extra |
| `README.md` | shown on the repo page (used as the package long-description) |
| `LICENSE` | MIT license text with your name/year |
| `CONTRIBUTING.md` | how others can contribute |
| `CHANGELOG.md` | notable changes per version |
| `.gitignore` | keep private/build files out of the repo |
| `.gitattributes` | `* text=auto` — deterministic line endings |
| `slimv/` | the Python package (`packages = ["slimv"]`) |
| `tests/` | the pytest suite |
| `docs/` | the Sphinx documentation |
| `landing/index.html` | the landing page (served at the Pages root) |
| `.github/workflows/ci.yml` | CI: run tests + build docs on push/PR |
| `.github/workflows/docs.yml` | CD: build + deploy the site to Pages |

Key `pyproject.toml` sections:

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "slimv"
version = "0.2.0"
readme = "README.md"
license = { text = "MIT" }
authors = [{ name = "Ahmed Abdelhaleem", email = "ahmedhal@gmail.com" }]
dependencies = ["rich>=13.0"]

[project.optional-dependencies]
test = ["pytest>=7"]

[project.scripts]
slimv = "slimv.cli:main"

[tool.setuptools]
packages = ["slimv"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

---

## 2. Build the distributable artifacts

```bash
cd <project root>
rm -rf dist build *.egg-info        # clean previous builds (PowerShell: Remove-Item -Recurse -Force dist,build,*.egg-info)
python -m build
```

Produces two files in `dist/`:
- `slimv-0.2.0-py3-none-any.whl` (wheel — the primary install)
- `slimv-0.2.0.tar.gz` (source distribution)

---

## 3. Test before shipping

```bash
pytest                              # 60 tests, ffmpeg-free, ~1s

# smoke-test the built wheel in a throwaway venv
python -m venv .venv-check
.venv-check\Scripts\Activate.ps1     # Linux/macOS: source .venv-check/bin/activate
pip install dist/slimv-0.2.0-py3-none-any.whl
slimv --version                      # -> slimv 0.2.0 By:...
deactivate
```

Build the docs to confirm they're warning-clean (the deploy uses `-W`):

```bash
python -m sphinx -b html docs/source docs/_build/html -W
```

---

## 4. Initialize the local git repo

```bash
cd <project root>
git init -b main
git add -A

# SANITY CHECK: make sure no private files are staged (should print nothing)
git ls-files | grep -iE "\.ps1$|profiles\.toml$|_build/|^dist/|egg-info"

git commit -m "slimv 0.2.0 — initial public release"
```

The `.gitignore` keeps build output, caches, and any private scripts out of the
commit automatically.

---

## 5. Create the GitHub repo and push

**CLI (creates the repo *and* pushes in one step):**

```bash
gh repo create abdelhaleemahmed/slimv --public --source=. --push \
  --description "Shrink video without visible quality loss — an ffmpeg-driven re-encoding toolkit"
```

If the push is rejected for the `workflow` scope, run the `gh auth refresh`
command from §0, then:

```bash
git push -u origin main
```

**Manual (web UI):** create an empty repo at github.com/new (no README/license),
then:

```bash
git remote add origin https://github.com/abdelhaleemahmed/slimv.git
git push -u origin main
```

---

## 6. Set repo metadata (About box)

**CLI:**

```bash
gh repo edit abdelhaleemahmed/slimv \
  --description "Shrink video without visible quality loss — an ffmpeg-driven re-encoding toolkit" \
  --homepage "https://abdelhaleemahmed.github.io/slimv/" \
  --add-topic video --add-topic ffmpeg --add-topic hevc --add-topic h265 \
  --add-topic transcoding --add-topic compression --add-topic vmaf \
  --add-topic cli --add-topic python --add-topic quicksync
```

**Manual:** repo page → the ⚙ next to **About** → fill in Description, Website,
and Topics.

---

## 7. Create the release (downloadable wheel + sdist)

A GitHub **Release** is what gives users a versioned download. Attach the built
artifacts from `dist/`.

**CLI** (this also creates the `v0.2.0` git tag):

```bash
gh release create v0.2.0 \
  dist/slimv-0.2.0-py3-none-any.whl dist/slimv-0.2.0.tar.gz \
  --repo abdelhaleemahmed/slimv \
  --title "slimv 0.2.0" \
  --notes-file RELEASE_NOTES.md      # or --notes "..." inline
```

**Manual:** repo → **Releases** → *Draft a new release* → choose/create tag
`v0.2.0` → title + notes → **drag the two files from `dist/`** into the assets
box → *Publish release*.

Users then install with:

```bash
pip install https://github.com/abdelhaleemahmed/slimv/releases/download/v0.2.0/slimv-0.2.0-py3-none-any.whl
# or:  pip install git+https://github.com/abdelhaleemahmed/slimv.git@v0.2.0
```

---

## 8. Enable GitHub Pages (GitHub Actions method)

The docs/landing are deployed by the `docs.yml` workflow using the official Pages
actions, so Pages must be set to build from **GitHub Actions** (not a branch).

**CLI (API):**

```bash
gh api --method POST repos/abdelhaleemahmed/slimv/pages -f build_type=workflow
# if it already exists, update instead:
gh api --method PUT  repos/abdelhaleemahmed/slimv/pages -f build_type=workflow
```

**Manual (required if the API call isn't used):** repo → **Settings** → **Pages**
→ **Build and deployment** → **Source: GitHub Actions**.

The site goes live at `https://abdelhaleemahmed.github.io/slimv/` after the next
deploy.

---

## 9. The CI/CD workflows (what runs automatically)

Once pushed, two workflows run on every push to `main`:

- **`ci.yml`** — installs the package with the `test` extra and runs `pytest` on
  Python 3.9 / 3.11 / 3.13, plus a docs build check. Also runs on pull requests.
- **`docs.yml`** — assembles the site and deploys it to Pages:
  - the **landing page** (`landing/index.html`) at the root,
  - the **Sphinx docs** under `/docs/`,
  - the social image copied to the root,
  - then `upload-pages-artifact` + `deploy-pages` publish it.

Watch a run:

```bash
gh run list  --repo abdelhaleemahmed/slimv --limit 5
gh run view  <run-id> --repo abdelhaleemahmed/slimv
```

Site structure after deploy:

| URL | Serves |
|-----|--------|
| `/slimv/` | landing page |
| `/slimv/docs/` | full documentation |
| `/slimv/social-preview.png` | share image |

---

## 10. Social preview image (manual — no API)

GitHub has no API to set the social preview, so upload it once by hand:

> repo → **Settings** → **General** → **Social preview** → **Edit** → upload
> `assets/social-preview.png` (1280×640).

This is the image shown when the repo link is shared on Slack/Twitter/Discord.

---

## Cutting a new release (the short version)

For every subsequent version (e.g. `0.2.1` / `0.3.0`):

```bash
# 1. bump the version in THREE places
#    - pyproject.toml            (version = "X.Y.Z")
#    - slimv/__init__.py         (__version__ = "X.Y.Z")
#    - docs/source/conf.py       (release / version)
# 2. add a CHANGELOG.md entry for X.Y.Z
# 3. test + build
pytest
rm -rf dist build *.egg-info && python -m build
# 4. commit + push (CI + docs deploy run automatically)
git add -A && git commit -m "slimv X.Y.Z" && git push
# 5. cut the release with the new artifacts
gh release create vX.Y.Z dist/slimv-X.Y.Z-py3-none-any.whl dist/slimv-X.Y.Z.tar.gz \
  --title "slimv X.Y.Z" --notes "..."
```

Pages redeploys itself from the push; only the release step is separate.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Push rejected: *"...without `workflow` scope"* | `gh auth refresh -h github.com -s workflow`, then push again (§0). |
| Pages deploy job fails at `deploy-pages` | Pages source isn't set to **GitHub Actions** — do §8. |
| Docs deploy fails on a warning | The build uses `-W`; fix the Sphinx warning locally with `python -m sphinx -b html docs/source docs/_build/html -W`. |
| A private file got committed | It's missing from `.gitignore`; add it, then `git rm --cached <file>` and commit. |
| `LF will be replaced by CRLF` warnings | Harmless; `.gitattributes` (`* text=auto`) normalizes this. |
| Release download 404 | The tag/assets don't exist yet — publish the release (§7). |
