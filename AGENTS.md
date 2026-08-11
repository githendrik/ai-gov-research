# AGENTS.md

Notes for any agent (Claude, GPT, opencode, etc.) working on this repo. Read this before touching anything.

## What this project is

Static site for **The AI Gov Digest** — a weekly AI governance/regulation/safety digest. Hugo + custom brutalist theme, deployed on Vercel, source content kept verbatim and transformed at build time. Bilingual (EN + DE): the upstream automation produces both languages in a single pass, the bridge splits and commits them, the transformer routes them to per-language content dirs, and Hugo serves them via its built-in i18n.

## The one rule

**Do not edit files in `docs/`.** They are produced by an upstream research pipeline and are the source of truth. The build transforms copies of them; the originals stay verbatim. If the format of `docs/*.md` needs to change, change the upstream generator — not the files in this repo.

## Architecture in one paragraph

`docs/*.md` + `docs/*.de.md` (verbatim, committed) + `static/images/*.png` (hero images, same base stem) → `scripts/transform_docs.py` runs at build time → writes `content/en/posts/*.md` and `content/de/posts/*.de.md` (gitignored, generated) with YAML frontmatter (title promoted from H1, date parsed from filename, slug set to base stem to prevent collisions, `image:` injected if matching PNG exists) and bracketed citations rewritten to `<sup>` → Hugo builds `public/` with EN at root and DE at `/de/`. No GitHub Actions; Vercel auto-deploys on push to `main`. The upstream pipeline (homelab CT 104) pushes both `docs/*.md` + `docs/*.de.md` and `static/images/*.png` via a deploy key.

## Stack choices and why

- **Hugo over Jekyll/Astro/Eleventy:** RSS built-in (no plugin), single Go binary (no Ruby/Node toolchain for the build), sub-second builds, Vercel auto-detects it. Chosen for a one-post-per-week, text-heavy digest.
- **Custom theme over community theme:** The site has one content type (weekly digest) with a known structure. A ~150-line hand-rolled theme beats fighting a community theme's templates when we want to style citation chips, Source/URL/Category fields, etc. Current theme is brutalist: boxed banner with hard offset shadow, orange (`--accent: #ff4500`) title block, monospace nav, 8px orange left-border on post titles.
- **Pre-build transformer over Hugo render hooks / content adapters:** Hugo's render hooks only cover link/heading/image nodes — they cannot rewrite arbitrary text like `[68]` citation markers, nor inject frontmatter. A ~60-line Python script run before `hugo` is the right tool. The script is idempotent and never touches `docs/`.
- **No GitHub Actions:** The weekly reminder workflow was removed because the upstream pipeline pushes content automatically. Vercel's native push-to-deploy handles everything. The upstream bridge script (homelab CT 104) commits `docs/*.md` and `static/images/*.png` via a deploy key.

## The upstream pipeline (homelab CT 104)

Content is produced by an automated research pipeline running on a Proxmox LXC container. Full reference: `Homelab/reference/gmktec-m6-local-llm-guide.md` §15 in the Obsidian vault. Summary:

1. **Open WebUI Automation** (weekly Mon 07:00) — `deepseek-v4-flash` via haimaker runs ~20 agentic SearXNG search rounds, produces a cited markdown digest in **English, followed by a `---DE---` delimiter and a German translation of the same digest** (identical item numbering, citations, URLs — only prose translated). The Knowledge Base "AI Governance Research" is attached to the model for RAG-based dedup (`rag.top_k = 20`).
2. **Bridge script** (`bridge.py`, systemd timer Mon 07:30) — extracts the digest from the chat API, splits on `---DE---`, writes `docs/<stem>.md` (EN) + `docs/<stem>.de.md` (DE) to the blog repo, runs a structural parity check (item headings + citation markers EN vs DE), generates a hero image via haimaker `gpt-image-1-mini` (1024×1024 → cropped to 16:9 with Pillow → compressed), saves to `static/images/` (shared by both languages), and pushes both markdown + image via a deploy key. Two commits per run: markdown first (fast), image second (slow, non-blocking if it fails).
3. **oikb watch** (systemd service, continuous) — syncs the digests directory into the Open WebUI Knowledge Base via incremental SHA-256 diff, so the KB grows weekly for RAG dedup.

The bridge does `git pull --rebase` before pushing, so manual edits to this repo (Hugo config, theme, etc.) are safe — the bridge rebases its commits on top.

## The transformer (`scripts/transform_docs.py`)

What it does, in order:
1. Globs `docs/*.md` (skips dotfiles). Detects language: files ending in `.de.md` are German, all others English.
2. Parses date from leading `YYYY-MM-DD` in the filename (works for both `*.md` and `*.de.md`).
3. Extracts the first `# ` line as `title` and removes that line from the body (so the theme's title doesn't duplicate it).
4. Injects YAML frontmatter: `title`, `date`, `draft: false`, `slug: <base-stem>` (full stem minus `.de` for German, to avoid collisions and share the URL namespace), `tags: [governance]`, `source: <filename>`, and `image: /images/<base-stem>.png` if `static/images/<base-stem>.png` exists (shared by both languages).
5. Rewrites `[NN]` and adjacent runs like `[77][93]` → `<sup>77,93</sup>`.
6. Writes EN to `content/en/posts/<same-filename>`, DE to `content/de/posts/<same-filename>`. Hugo's i18n picks these up via per-language `contentDir` in `hugo.toml`.

Source `docs/*.md` is never modified. Re-running overwrites prior output (idempotent). Supports `--watch` via `watchdog` (falls back to polling if `watchdog` isn't installed).

## Hero images

Each post can have a hero image stored as `static/images/<base-stem>.png` (same base stem as the markdown, e.g. `2026-08-04-ai-governance.png` for `2026-08-04-ai-governance.md`). The transformer checks for a matching PNG and injects `image: /images/<base-stem>.png` into the frontmatter. Both EN and DE posts share the same hero image (same base stem). If no PNG exists, no `image` field is added and the post renders without a hero — the template uses `{{ with .Params.image }}` with a plain-title fallback.

Images are generated by the upstream bridge script (haimaker `gpt-image-1-mini`, 1024×1024) and cropped to 16:9 center + compressed with Pillow before pushing. They live in `static/images/` (not `assets/images/`) because Hugo serves `static/` as-is — `assets/` is for resources that need Hugo pipeline processing.

The Hugo template (`single.html`) renders the hero with a brutalist title overlay: an orange (`--accent: #ff4500`) block at the bottom of the image with black text and a 4px black top border. Contrast is guaranteed by the solid block, not by text shadows or gradients. On mobile (`max-width: 480px`), font size and hero height scale down via `clamp()`.

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

Two feeds per language, both auto-generated by Hugo:
- EN: `/index.xml` (site-wide) and `/posts/index.xml` (posts section)
- DE: `/de/index.xml` (site-wide) and `/de/posts/index.xml` (posts section)

Configured in `hugo.toml` via `[outputs]` (home and section both emit `rss`) and `[services.rss] limit = 50`.

## Domain

`aigov.philine.ch` — set in `hugo.toml` `baseURL`. Update there if the domain changes.

## Newsletter

ESP: **Brevo**, Free plan. 300 emails/day cap, unlimited contacts. Full plan: `NEWSLETTER_PLAN.md`.

- **Sender:** `digest@aigov.philine.ch` (Brevo sender id 2). Domain verified via `brevo-code` TXT on `aigov.philine.ch`. DKIM via CNAME delegation to `brevo1._domainkey` / `brevo2._domainkey` → `b1.aigov-philine-ch.dkim.brevo.com` / `b2...`. SPF TXT (`v=spf1 include:spf.brevo.com ~all`) still pending — add to DNS for full deliverability.
- **Sending** is triggered by the bridge on CT 104 via `POST /v3/emailCampaigns` + `POST /v3/emailCampaigns/{id}/sendNow` — **not** RSS, **not** GitHub Actions. The endpoint is `/sendNow`, not `/send` (Brevo returns 404 on `/send`).
- **Email HTML builder:** `scripts/build_email.py` — reads a rendered Hugo post from `public/posts/<slug>/index.html`, extracts `.post-content`, wraps it in a brutalist email template with inline CSS (table-based, `border-collapse:collapse`, 4px black borders, orange `#ff4500` title block, monospace labels). No hero image — email clients (Gmail, Apple Mail) block remote images or render them as broken icons. Run after `hugo` builds: `python3 scripts/build_email.py posts/<slug>/`.
- **API key** lives in the bridge's systemd env (`BREVO_KEY`), never in this repo. Key is **scoped** to campaigns endpoints; Brevo IP whitelist is **not** enabled (home ISP IP is dynamic).
- **Footer signup form:** planned (see `NEWSLETTER_PLAN.md` §3) — Brevo JS-iframe embed, form IDs will live in `[params.newsletter]` in `hugo.toml`. Not yet implemented.
- **DMARC gotcha:** `richert.li` has a DMARC policy that blocks Brevo from sending as `brevo@richert.li`. Use `digest@aigov.philine.ch` only. The `aigov.philine.ch` subdomain was on a Vercel CNAME — switched to A record (`76.76.21.21`) to allow TXT records to coexist (CNAME + TXT on the same name is RFC-illegal).
- If a fixed egress IP becomes required: relay through the Oracle VPS (fixed IP). See `NEWSLETTER_PLAN.md` §5.
- Don't hand-roll a plain HTML POST form for the footer (would expose the API key on a static site).
- Don't remove the `enabled` gate in `hugo.toml` (used to toggle without code removal).
- Don't include hero images in email HTML — email clients block them.

## What NOT to do

- Don't edit `docs/*.md` or `docs/*.de.md` by hand (upstream pipeline owns them).
- Don't edit `static/images/*.png` by hand (upstream pipeline generates them).
- Don't commit `content/en/posts/*.md` or `content/de/posts/*.md` (gitignored; generated).
- Don't rename `hugo.toml` to `config.toml` to "fix" the version issue — bump `HUGO_VERSION` on Vercel instead.
- Don't remove the explicit `slug` from the transformer's frontmatter (weekly posts will collide).
- Don't add a GitHub Actions weekly reminder workflow — the upstream pipeline pushes automatically.
- Don't introduce a community Hugo theme without strong reason; the custom one is intentional and ~150 lines.
- Don't move images from `static/images/` to `assets/images/` — `assets/` is for Hugo pipeline resources, `static/` is served as-is.
- Don't add comments to code unless asked (repo convention).

## Lint / typecheck

No linter or typecheck is wired up. The transformer is plain Python 3.9+ (no deps beyond stdlib + optional `watchdog`). Hugo validates config at build time. If something breaks, `hugo --minify --gc` and `python3 scripts/transform_docs.py` are the smoke tests.
