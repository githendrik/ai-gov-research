# AGENTS.md

Notes for any agent (Claude, GPT, opencode, etc.) working on this repo. Read this before touching anything.

## What this project is

Static site for **The AI Gov Digest** — a weekly AI governance/regulation/safety digest. Hugo + custom brutalist theme, deployed on Vercel, source content kept verbatim and transformed at build time.

## The one rule

**Do not edit files in `docs/`.** They are produced by an upstream research pipeline and are the source of truth. The build transforms copies of them; the originals stay verbatim. If the format of `docs/*.md` needs to change, change the upstream generator — not the files in this repo.

## Architecture in one paragraph

`docs/*.md` (verbatim, committed) → `scripts/transform_docs.py` runs at build time → writes `content/posts/*.md` (gitignored, generated) with YAML frontmatter (title promoted from H1, date parsed from filename, slug set to full stem to prevent collisions) and bracketed citations rewritten to `<sup>` → Hugo builds `public/`. No GitHub Actions; Vercel auto-deploys on push to `main`.

## Stack choices and why

- **Hugo over Jekyll/Astro/Eleventy:** RSS built-in (no plugin), single Go binary (no Ruby/Node toolchain for the build), sub-second builds, Vercel auto-detects it. Chosen for a one-post-per-week, text-heavy digest.
- **Custom theme over community theme:** The site has one content type (weekly digest) with a known structure. A ~150-line hand-rolled theme beats fighting a community theme's templates when we want to style citation chips, Source/URL/Category fields, etc. Current theme is brutalist: boxed banner with hard offset shadow, orange (`--accent: #ff4500`) title block, monospace nav, 8px orange left-border on post titles.
- **Pre-build transformer over Hugo render hooks / content adapters:** Hugo's render hooks only cover link/heading/image nodes — they cannot rewrite arbitrary text like `[68]` citation markers, nor inject frontmatter. A ~60-line Python script run before `hugo` is the right tool. The script is idempotent and never touches `docs/`.
- **No GitHub Actions:** The weekly reminder workflow was removed because the user's upload process is already automated. Vercel's native push-to-deploy handles everything. If scheduled automation is needed later, add it back as a cron that commits to `docs/` (not a reminder issue).

## The transformer (`scripts/transform_docs.py`)

What it does, in order:
1. Globs `docs/*.md` (skips dotfiles).
2. Parses date from leading `YYYY-MM-DD` in the filename.
3. Extracts the first `# ` line as `title` and removes that line from the body (so the theme's title doesn't duplicate it).
4. Injects YAML frontmatter: `title`, `date`, `draft: false`, `slug: <full-stem>` (collision guard), `tags: [governance]`, `source: <stem>.md`.
5. Rewrites `[NN]` and adjacent runs like `[77][93]` → `<sup>77,93</sup>`.
6. Writes to `content/posts/<same-filename>`.

Source `docs/*.md` is never modified. Re-running overwrites prior output (idempotent). Supports `--watch` via `watchdog` (falls back to polling if `watchdog` isn't installed).

## The collision slug gotcha

Hugo's default slug strips the leading `YYYY-MM-DD` from filenames. So `2026-08-04-ai-governance.md` and `2026-08-11-ai-governance.md` both slugify to `ai-governance` and overwrite each other. The transformer sets `slug: <full-stem>` explicitly to avoid this. If you ever remove that line, weekly posts will collide. Don't.

## The Hugo version gotcha (most likely thing to break)

Vercel's default Hugo runtime is **0.58.2** (from 2019). It predates `hugo.toml` support (added in v0.110.0, Feb 2023). Symptoms when the version is wrong:
- Site builds "successfully" (no build error)
- Custom CSS loads (assets don't depend on config values) — so the red header bar appears
- But `{{ .Site.Title }}`, `{{ .Site.BaseURL }}`, `{{ .Site.Params.description }}` all render **empty**
- Result: title text missing, all internal links `href=""`, meta description blank
- `generator` meta tag reads `Hugo 0.58.2` instead of the current version

**Fix:** set `HUGO_VERSION=0.164.0` (or any ≥ 0.110.0) as a Vercel environment variable. Do not try to "fix" by renaming `hugo.toml` to `config.toml` — 0.58.2 is too old for `defaultContentLanguage`, modern Goldmark config, `services.rss`, etc., and you'll be patching regressions for hours.

**Diagnostic shortcut:** `document.querySelector('meta[name=generator]').getAttribute('content')` in the browser console. If it says `0.58.x`, it's the version issue.

## Local toolchain

- Hugo: `brew install hugo` (currently v0.164.0+extended+withdeploy on the maintainer's machine)
- Python: 3.9+ (system python on macOS works)
- Node: only needed for `concurrently` in `npm run dev`; the build itself has no Node dependency

## Commands

```bash
# Dev (hot reload on docs/ changes)
npm run dev

# Build (what Vercel runs)
python3 scripts/transform_docs.py && hugo --minify --gc

# Just the transformer
python3 scripts/transform_docs.py
python3 scripts/transform_docs.py --watch

# Just Hugo
hugo server --port 1313
```

## RSS

Two feeds, both auto-generated by Hugo:
- `/index.xml` — site-wide
- `/posts/index.xml` — posts section only

Configured in `hugo.toml` via `[outputs]` (home and section both emit `rss`) and `[services.rss] limit = 50`.

## Domain

`aigov.philine.ch` — set in `hugo.toml` `baseURL`. Update there if the domain changes.

## What NOT to do

- Don't edit `docs/*.md` by hand (upstream pipeline owns them).
- Don't commit `content/posts/*.md` (gitignored; generated).
- Don't rename `hugo.toml` to `config.toml` to "fix" the version issue — bump `HUGO_VERSION` on Vercel instead.
- Don't remove the explicit `slug` from the transformer's frontmatter (weekly posts will collide).
- Don't add a GitHub Actions weekly reminder workflow — upload is already automated.
- Don't introduce a community Hugo theme without strong reason; the custom one is intentional and ~150 lines.
- Don't add comments to code unless asked (repo convention).

## Lint / typecheck

No linter or typecheck is wired up. The transformer is plain Python 3.9+ (no deps beyond stdlib + optional `watchdog`). Hugo validates config at build time. If something breaks, `hugo --minify --gc` and `python3 scripts/transform_docs.py` are the smoke tests.
