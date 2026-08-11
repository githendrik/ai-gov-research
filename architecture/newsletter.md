# Newsletter

The AI Gov Digest sends a weekly email newsletter via **Brevo** (Free plan) — one campaign per language (EN + DE), triggered automatically by the bridge on CT 104 after the markdown + image push. Subscribers sign up via a Brevo-hosted signup form embedded in the site footer.

## Architecture

```
┌─ Site footer (Hugo) ──────────────────────────────────────────────┐
│                                                                   │
│  layouts/partials/newsletter.html                                 │
│    reads form_url from hugo.toml [params.newsletter.<lang>]        │
│    renders Brevo iframe (540×520, scrolling=auto)                 │
│  → subscriber submits email + GDPR checkbox                       │
│  → Brevo double opt-in → contact lands on ai-gov-en / ai-gov-de  │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘

┌─ CT 104 bridge.py (weekly, after image push) ────────────────────┐
│                                                                   │
│  send_newsletter(stem, date_str, de_content)                     │
│    1. python3 scripts/transform_docs.py  (blog-repo)             │
│    2. hugo --minify --gc                    (blog-repo)           │
│    3. python3 scripts/build_email.py posts/<stem>/  → email HTML │
│    4. POST /v3/emailCampaigns  (EN, list ai-gov-en id 4)          │
│    5. POST /v3/emailCampaigns/{id}/sendNow                       │
│    6. Repeat for DE (list ai-gov-de id 5, German subject)         │
│    Non-blocking — markdown ships even if email send fails.       │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

## Components

| Component | Location | Purpose |
|---|---|---|
| `hugo.toml` `[params.newsletter]` | This repo | `enabled` gate + per-language `form_url` (Brevo iframe URLs) |
| `layouts/partials/newsletter.html` | This repo | Renders Brevo iframe in the footer, language-switched |
| `layouts/_default/baseof.html` | This repo | Footer includes newsletter box when `enabled = true` |
| `i18n/en.yaml` + `i18n/de.yaml` | This repo | `newsletter_title` + `newsletter_note` strings |
| `assets/css/main.css` | This repo | `.newsletter-box` brutalist styling (boxed, inset orange bar, hard shadow) |
| `scripts/build_email.py` | This repo (also on CT 104) | Reads rendered Hugo post HTML, wraps in brutalist email template with inline CSS |
| `/usr/local/bin/hugo` | CT 104 | Hugo extended v0.134.0 — builds site locally for email HTML generation |
| `/opt/ai-gov-research/.brevo_env` | CT 104 (perms 600) | `BREVO_KEY`, `BREVO_EN_LIST_ID=4`, `BREVO_DE_LIST_ID=5`, `BREVO_SENDER_EMAIL` |
| `bridge.py` `send_newsletter()` | CT 104 | Appended after image push — builds email HTML, creates + sends Brevo campaigns |
| `ai-gov-bridge.service` | CT 104 | systemd oneshot — loads `.brevo_env` via `EnvironmentFile=` |

## Brevo account

- **ESP:** Brevo, Free plan. 300 emails/day cap, unlimited contacts.
- **Sender:** `digest@aigov.philine.ch` (Brevo sender id 2, active). Domain verified.
- **Contact lists:** `ai-gov-en` (id 4), `ai-gov-de` (id 5). Test list `ai-gov-test-en` (id 3) kept for dry-runs.
- **Signup forms:** Two forms (EN + DE) in Brevo's drag&drop builder. Email field + GDPR consent checkbox, double opt-in enabled. Form URLs stored in `hugo.toml`.
- **Account email:** `brevo@richert.li` (login only — DMARC on `richert.li` blocks Brevo from sending as this address; use `digest@aigov.philine.ch` only).
- **IP whitelist:** Not enabled (home ISP IP is dynamic). Key is the secret; no IP restriction needed.

## DNS setup

`aigov.philine.ch` was switched from a Vercel CNAME to an A record to allow TXT records to coexist (CNAME + TXT on the same name is RFC-illegal).

| Type | Name | Value |
|---|---|---|
| A | `aigov.philine.ch` | `76.76.21.21` (Vercel) |
| TXT | `aigov.philine.ch` | `brevo-code:3cdc2538ee66a8320dad17a3075968c6` |
| TXT | `aigov.philine.ch` | `v=spf1 include:spf.brevo.com ~all` |
| CNAME | `brevo1._domainkey.aigov.philine.ch` | `b1.aigov-philine-ch.dkim.brevo.com` |
| CNAME | `brevo2._domainkey.aigov.philine.ch` | `b2.aigov-philine-ch.dkim.brevo.com` |

Vercel serves the site fine via A record (routes by Host header, not IP). No Vercel config changes needed beyond swapping the DNS record type.

## Email HTML

`scripts/build_email.py` reads a rendered Hugo post from `public/posts/<slug>/index.html` (or `public/de/posts/<slug>/` for DE), extracts `.post-content`, and wraps it in a brutalist email template:

- **Table-based layout** with `border-collapse:collapse` (email-client safe).
- **4px solid black borders** on banner, title block, and content box — the core brutalist look.
- **Orange `#ff4500` title block** with black bold title + monospace date.
- **`<sup>` citations** styled with muted color + small font size.
- **Inline CSS** on all elements (email clients strip `<style>` blocks).
- **No hero image** — email clients (Gmail, Apple Mail) block remote images or render them as broken icons. The title block carries the aesthetic without images.
- **No `box-shadow`** — Gmail/Outlook strip it. The 4px borders + orange blocks read as "brutalist enough" without the offset shadow. If wanted, the table-fake-shadow trick (nested offset cells filled with `#1a1a1a`) can be added later.

Run locally: `python3 scripts/build_email.py posts/<slug>/` (after `hugo` builds). Output: `scripts/email_output.html`.

## Brevo API

- **Create campaign:** `POST /v3/emailCampaigns` with `name`, `subject`, `sender`, `htmlContent`, `recipients.listIds`.
- **Send immediately:** `POST /v3/emailCampaigns/{id}/sendNow` — **not** `/send` (Brevo returns 404 on `/send`).
- **User-Agent:** Brevo's Cloudflare blocks the default Python urllib UA. Use `ai-gov-bridge/1.0` or similar.
- **Queue delay:** Campaigns show `status: queued` for ~1 min before flipping to `sent`. Normal.

## Egress IP — Brevo API key whitelist

Brevo's IP whitelist is optional and **not enabled**. The home ISP IP is dynamic, so whitelisting would break the weekly send whenever the ISP reassigns one. The API key itself is the secret; no IP restriction needed.

Belt-and-suspenders hardening that does *not* need a fixed IP:
- **Scope the API key** to only the campaigns endpoints. Brevo supports per-key endpoint scoping.
- **Store the key in the bridge's systemd env** (`/opt/ai-gov-research/.brevo_env`), never in this repo.
- **Rotate the key** if CT 104 is compromised.

If a fixed egress IP ever becomes required, relay through the Oracle VPS (fixed IP): run a minimal HTTPS endpoint on the VPS that accepts the campaign payload from CT 104, injects the `api-key` header, and forwards to `api.brevo.com`. Whitelist the Oracle VPS IP in Brevo.

The existing Cloudflare Tunnel on the Proxmox host is an **ingress** tool — it does not give the bridge a fixed egress IP. Don't rely on it for this.

## Evaluation: why Brevo Free

Use case: ≤100 subscribers, 1 email/week (~400 emails/mo), fully automated via the bridge, bilingual EN/DE.

| Requirement | Brevo Free | Verdict |
|---|---|---|
| Subscriber cap | Unlimited | ✅ |
| Email volume | 300/day (~9k/mo) | ✅ 100/week << 300/day |
| API-triggered campaign send on Free | `POST /v3/emailCampaigns` + `/sendNow` | ✅ |
| Embedded signup form | Drag&drop builder, iframe embed, double opt-in, GDPR | ✅ |
| Free-tier branding | "Sent with Brevo" footer | ⚠️ Acceptable |
| Account approval | One-time anti-spam review (~24h) | ⚠️ One-time friction |
| RSS-to-email | Not a first-class free feature | ➖ Bridge orchestrates instead |

Best of the evaluated free tiers. MailerLite Free blocks API sending; Mailchimp Free has no automation/scheduling and only 500 emails/mo; Kit Free has no RSS but does have API + 10k subs. Brevo is the only one whose free API lets the bridge trigger a real campaign send with zero weekly manual work.

## Gotchas

- **DMARC on `richert.li`** blocks Brevo from sending as `brevo@richert.li`. Use `digest@aigov.philine.ch` only.
- **CNAME + TXT on the same name is RFC-illegal** — `aigov.philine.ch` had a Vercel CNAME; had to switch to A record to add Brevo TXT records.
- **DE post slug strips `.de`** — Hugo's frontmatter `slug:` is the full stem minus `.de`, so `2026-08-10-ai-governance.de.md` renders at `public/de/posts/2026-08-10-ai-governance/index.html`. `build_email.py` routes by `lang` param, not by stem suffix.
- **Brevo `/sendNow` endpoint** — use `/sendNow`, not `/send` (404 on `/send`).
- **Brevo Cloudflare blocks default Python UA** — use `ai-gov-bridge/1.0` or similar custom User-Agent.
- **Sent campaigns can't be deleted** — Brevo returns 403 `permission_denied`. Test campaigns are permanent records.
- **Brevo free footer** ("Sent with Brevo") appears on every email. Unavoidable on Free.
- **300/day cap** is fine at ≤100 subs × 1/week, but will bite if the list exceeds ~300 active subs on a single send day. Monitor; upgrade before that point.

## Validation history

- **2026-08-10:** First end-to-end test send (campaigns 1 + 2). Confirmed Brevo API works, brutalist email HTML renders, DKIM passes Gmail/Apple Mail. Discovered hero images don't render in email clients — removed from template.
- **2026-08-10:** Footer signup forms created in Brevo, iframe URLs wired into `hugo.toml`, `enabled = true`. DOI flow tested with real emails — contacts land on `ai-gov-en` / `ai-gov-de`.
- **2026-08-11:** Bridge wired on CT 104. Hugo extended v0.134.0 installed, `build_email.py` copied, `bridge.py` updated with `send_newsletter()`, `.brevo_env` created, systemd service updated. Test campaigns 8 (EN) + 9 (DE) sent from CT 104. Full pipeline validated: `transform_docs.py` → `hugo` → `build_email.py` → Brevo API → campaigns sent.

## What NOT to do

- Don't use `brevo@richert.li` as a campaign sender (DMARC blocks it).
- Don't hand-roll a plain HTML POST form for the footer (would expose the API key on a static site).
- Don't remove the `enabled` gate in `hugo.toml` (used to toggle without code removal).
- Don't include hero images in email HTML — email clients block them.
- Don't enable the Brevo IP whitelist (home ISP IP is dynamic).
- Don't commit `BREVO_KEY` or `.brevo_env` to this repo.
