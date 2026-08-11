# Newsletter integration plan — Brevo Free + Hugo footer signup

Status: **plan only — not implemented**. Created 2026-08-10.

## 1. Evaluation: Brevo Free for this project

Use case: ≤100 subscribers, 1 email/week (≈400 emails/mo), fully automated "push and forget" via the bridge on CT 104, bilingual EN/DE.

| Requirement | Brevo Free | Verdict |
|---|---|---|
| Subscriber cap | **Unlimited** | ✅ No 250-sub wall |
| Email volume | **300/day (~9k/mo)** | ✅ 100/week << 300/day |
| API-triggered marketing campaign send on Free | `POST /v3/emailCampaigns` + `/send` | ✅ Confirmed in API docs |
| Embedded signup form | Drag&drop builder, JS-iframe embed, double opt-in, GDPR | ✅ |
| Free-tier branding | "Sent with Brevo" footer on emails | ⚠️ Acceptable for a personal digest |
| Account approval | One-time anti-spam review (~24h) before sending enabled | ⚠️ One-time friction |
| RSS-to-email (native) | Not a first-class free feature | ➖ Not used — bridge orchestrates instead |

**Fit:** Best of the evaluated free tiers (MailerLite, Mailchimp, Kit, Brevo). MailerLite Free blocks API sending and RSS campaigns; Mailchimp Free has no automation/scheduling and only 500 emails/mo; Kit Free has no RSS but does have API + 10k subs. Brevo is the only one whose free API lets the existing bridge trigger a real campaign send with zero weekly manual work.

**Caveats to verify on signup:**
1. Marketing-campaign send via API (not just transactional) — run one test send to a list of one.
2. Account sending approval delay.
3. Brevo JS form embed loads a script from `sibforms.com` (iframe). The inner form is styled in Brevo's builder, not via the host site's CSS — surrounding footer can be brutalist, inner form approximates.

## 2. Brevo account setup (one-time, outside this repo)

1. Create a Brevo account (no credit card). Complete sender-domain verification for `aigov.philine.ch`.
2. Wait for sending approval (~24h). Run a test campaign to one address to confirm marketing-campaign API send works on Free.
3. Create **two contact lists**: `ai-gov-en`, `ai-gov-de`.
4. Create **two senders**: EN sender (`digest@aigov.philine.ch`, name "The AI Gov Digest") and DE sender (same address, German name) — or one sender reused for both.
5. Create **two signup forms** (one per language) in the drag&drop builder:
   - Email field only + GDPR consent checkbox.
   - Enable **double opt-in**.
   - On submit → add to the matching list (`ai-gov-en` or `ai-gov-de`).
   - Grab the **embed code** (JS snippet) for each — note the form ID/UUID in the embed URL.
6. Generate an **API key** (Settings → API Keys). Store it in the CT 104 bridge's systemd environment as `BREVO_API_KEY` (never in this repo).

## 3. Repo changes — Hugo footer signup

Five files. No `docs/` or `static/images/` touched.

### 3.1 `hugo.toml` — add newsletter param block

Append at root (not under `[languages]` — one form per language, switched by `.Lang`):

```toml
[params.newsletter]
  enabled = true
  [params.newsletter.en]
    form_id = "<EN form UUID from Brevo embed URL>"
  [params.newsletter.de]
    form_id = "<DE form UUID from Brevo embed URL>"
```

Gate with `enabled` so it can be turned off without code removal.

### 3.2 `layouts/partials/newsletter.html` — new partial

Holds the Brevo JS embed snippet for the current language's form. Reads the form ID from `.Site.Params.newsletter.<lang>.form_id`. Wraps the Brevo `<script src="https://sibforms.com/forms/view/form/<ID>">` in a brutalist container with the i18n label above it. No hand-rolled HTML form — the iframe is required because a plain POST would expose the API key (unacceptable for a static site with no backend).

### 3.3 `layouts/_default/baseof.html:48-50` — add newsletter row to footer

Replace the single `<p>` footer with a two-row footer:

```
<footer class="site-footer">
  {{ with .Site.Params.newsletter }}
    {{ if .enabled }}
      <div class="newsletter-box">
        {{ partial "newsletter.html" $ }}
      </div>
    {{ end }}
  {{ end }}
  <p>&copy; {{ now.Format "2006" }} {{ .Site.Title }} · <a href="{{ "index.xml" | relLangURL }}">{{ T "rss" }}</a></p>
</footer>
```

### 3.4 `i18n/en.yaml` + `i18n/de.yaml` — add newsletter strings

```
# en.yaml
newsletter_title: "Get the weekly digest in your inbox"
newsletter_note: "One email per week. No spam. Unsubscribe anytime."

# de.yaml
newsletter_title: "Den wöchentlichen Digest ins Postfach"
newsletter_note: "Eine E-Mail pro Woche. Kein Spam. Jederzeit abbestellbar."
```

### 3.5 `assets/css/main.css` — brutalist styling for `.newsletter-box`

Match the existing banner idiom: boxed, hard offset shadow, `--accent: #ff4500` left border (8px, like post titles), monospace label, mobile scaling via `clamp()` on `max-width: 480px`. The Brevo iframe inside is styled via Brevo's builder (set form background to `#fff`, button to `#ff4500`, text to `#000`) to approximate.

## 4. Bridge on CT 104 — API send step (outside this repo)

Append to `bridge.py` after the existing image push, so the full weekly sequence is: digest → split EN/DE → push markdown → push image → **send newsletter**.

Per language (EN then DE):

1. Build the email HTML. Reuse the already-transformed post HTML (`content/en/posts/<stem>.md` rendered) or render a stripped digest template. Keep `<sup>` citations. Inline minimal CSS for email clients.
2. `POST https://api.brevo.com/v3/emailCampaigns` with:
   - `name`: `AI Gov Digest — <YYYY-MM-DD> (EN)`
   - `subject`: e.g. `AI Governance Weekly — <date>` (derive from title)
   - `sender`: `{"name": "The AI Gov Digest", "email": "digest@aigov.philine.ch"}`
   - `htmlContent`: the built HTML string
   - `recipients.listIds`: `[<EN list id>]`
   - `scheduledAt`: optional, e.g. 09:00 UTC Monday
3. Capture `id` from the 201 response.
4. Send: `POST https://api.brevo.com/v3/emailCampaigns/<id>/send` (immediate) — or rely on `scheduledAt`.
5. Repeat for DE with the DE list, DE sender, German subject, and DE HTML.

Requires `BREVO_API_KEY`, `BREVO_EN_LIST_ID`, `BREVO_DE_LIST_ID`, `BREVO_SENDER_EMAIL` in the bridge's systemd environment. Failure here should be **non-blocking** (like the image push) — markdown still ships even if the email send fails.

## 5. Egress IP — Brevo API key whitelist

### The problem

Brevo offers an optional **IP whitelist** per API key: if set, only requests from the listed IPs are accepted; all others get 401. The maintainer's home ISP does **not** assign a fixed IP — it changes occasionally. The bridge on CT 104 (Proxmox LXC) egresses via the home connection, so a whitelisted IP would break the weekly send whenever the ISP reassignes one.

### Recommendation: don't enable the IP whitelist

Brevo's IP whitelist is **optional** — leave the field empty and the key works from any IP. The API key itself is the secret. This is the zero-cost, zero-ops path and is **recommended** unless Brevo forces a whitelist at some future point.

Belt-and-suspenders hardening that does *not* need a fixed IP:

- **Scope the API key** to only the campaigns endpoints (`POST /emailCampaigns`, `POST /emailCampaigns/{id}/send`, `GET /emailCampaigns/{id}`). Brevo supports per-key endpoint scoping. A leaked scoped key can't read contacts or send transactional mail.
- **Store the key in the bridge's systemd env** (already the plan), never in this repo.
- **Rotate the key** if CT 104 is compromised.

### Fallback if a fixed egress IP becomes required

If Brevo ever mandates a whitelist (or you want one for defense-in-depth), three options, in order of preference given the existing homelab:

1. **Relay through the Oracle VPS (fixed IP) — recommended fallback.** The maintainer already has an Oracle Cloud VPS with a fixed IP. Run a tiny relay on it:
   - A minimal HTTPS endpoint (e.g. a 20-line Python `aiohttp`/Flask app or a Caddy reverse proxy) that accepts the campaign payload from CT 104, injects the `api-key` header, and forwards to `api.brevo.com`.
   - Or move the entire Brevo-send *step* off CT 104 and onto the Oracle VPS: CT 104 pushes the built HTML to the VPS (or to a shared object store), and a systemd timer on the VPS triggers the Brevo send. This keeps the Brevo key off the homelab entirely.
   - Whitelist the **Oracle VPS IP** in Brevo. Fixed, stable, free (existing resource).
   - Auth between CT 104 and the relay: a shared secret header over HTTPS, or mTLS. Keep it simple — one shared long token in both systemd envs is fine for a one-user relay.

2. **Cloudflare Worker as proxy.** Deploy a Worker that forwards to `api.brevo.com` with the key stored as a Worker secret. Bridge calls the Worker. Brevo sees Cloudflare's egress — but Workers egress IPs are shared/rotating, so you'd whitelist Cloudflare's published IP ranges, not one IP. Reuses the existing Cloudflare Tunnel account. Free up to 100k req/day. Downside: Brevo may not accept a CIDR-range whitelist (only single IPs), which would rule this out — verify before investing.

3. **Do nothing.** Don't enable the whitelist. This is the default and the recommended path.

### What the Cloudflare Tunnel cannot do here

The existing Cloudflare Tunnel on the Proxmox host is an **ingress** tool — it forwards inbound requests *to* homelab services. Outbound calls from the bridge to `api.brevo.com` still exit via the home ISP, not via Cloudflare. The Tunnel does not give the bridge a fixed egress IP. Don't rely on it for this.

### Decision

Default: **don't enable the Brevo IP whitelist; scope the key instead.** If a fixed IP becomes necessary, **relay through the Oracle VPS** (option 1). Document the chosen path in AGENTS.md (section 6) once decided.

## 6. Validation / testing

- **Local:** `hugo server --port 1313`, confirm footer form renders on both `/` and `/de/`, confirm iframe loads.
- **Signup flow:** submit a real email in EN and DE, confirm double-opt-in emails arrive and confirmations add to the right list.
- **Bridge:** dry-run with a one-address test list before pointing at the real list. Confirm the campaign appears in Brevo and sends.
- **Vercel:** deploy, re-test the form in production (CSP/X-Frame-Options must allow `sibforms.com`).
- **Smoke:** `python3 scripts/transform_docs.py && hugo --minify --gc` still passes.

## 7. AGENTS.md — add a "Newsletter" section

Concise, matching existing style:

- ESP: Brevo, Free plan. 300 emails/day cap, unlimited contacts.
- Footer form is a Brevo JS-iframe embed; form IDs live in `[params.newsletter]` in `hugo.toml`; inner form styled in Brevo's builder.
- Sending is triggered by the bridge on CT 104 via `POST /v3/emailCampaigns` + `/send` — **not** RSS, **not** GitHub Actions.
- API key lives in the bridge's systemd env, never in this repo. Key is **scoped** to campaigns endpoints; Brevo IP whitelist is **not** enabled (home ISP IP is dynamic).
- If a fixed egress IP becomes required: relay through the Oracle VPS (fixed IP). See `NEWSLETTER_PLAN.md` §5.
- Do not hand-roll a plain HTML POST form for the footer (would expose the API key on a static site).
- Do not remove the `enabled` gate in `hugo.toml` (used to toggle without code removal).

## 8. Risks / open items

- **Brevo free footer** appears on every sent email ("Sent with Brevo"). Removing it requires a paid plan. Acceptable tradeoff for $0.
- **300/day cap** is fine at ≤100 subs × 1/week, but will bite if the list exceeds ~300 active subs on a single send day. Monitor; upgrade to a paid Brevo tier before that point.
- **JS-iframe dependency:** the signup form requires `sibforms.com` to load. If Brevo has an outage, the form is blank but the rest of the site is unaffected. Acceptable.
- **Email HTML rendering:** email clients are picky. The first real send should be eyeballed in Gmail + Apple Mail. Inlining CSS is likely needed.
- **Two lists vs one segmented list:** Brevo supports segments. Two simple lists (EN/DE) is easier to reason about and matches the bilingual architecture; revisit if segments become useful.
- **Brevo IP whitelist:** not enabled by default (home ISP IP is dynamic). If Brevo mandates it, the Oracle VPS relay (§5 option 1) is the documented fallback. Verify the whitelist field's behavior on signup.

## 8a. Open points — validation session 2026-08-10

Status after first end-to-end test send (campaigns 1 + 2 to hendrik.richert@gmail.com + philine.richert@gmail.com). Send path works; the following items remain:

### DNS (user action, low urgency)

1. **SPF TXT record missing.** `aigov.philine.ch` has `brevo-code` verification TXT + DKIM (CNAME delegation to `brevo1._domainkey` / `brevo2._domainkey`), but **no SPF** (`v=spf1 include:spf.brevo.com ~all`). DKIM alone passed Gmail/Apple Mail delivery (not in spam), but SPF is belt-and-suspenders for deliverability. Add as a second TXT on `aigov.philine.ch` (Hoststar allows multiple TXT on the same name — if not, combine into one record: `"brevo-code:..." "v=spf1 include:spf.brevo.com ~all"`).

### Footer signup form (§3 — code prepped, IDs needed)

2. **Brevo signup forms not yet created.** All 5 Hugo files are prepped with placeholder form IDs and `enabled = false`:
   - `hugo.toml` — `[params.newsletter]` block with `enabled` gate + `en.form_id` / `de.form_id` placeholders
   - `layouts/partials/newsletter.html` — Brevo JS-iframe embed, language-switched via `.Site.Language.Lang`
   - `layouts/_default/baseof.html` — footer renders `.newsletter-box` when enabled
   - `i18n/en.yaml` + `i18n/de.yaml` — `newsletter_title` + `newsletter_note` strings
   - `assets/css/main.css` — `.newsletter-box` brutalist styling (boxed, inset 12px orange bar, 8px hard shadow, monospace label)
   
   **To activate:** create two signup forms in Brevo dashboard (Contacts → Forms → drag&drop builder). Each form: email field + GDPR consent checkbox, double opt-in enabled, adds to the matching list (`ai-gov-test-en` id 3 for EN; a new `ai-gov-test-de` list for DE). Grab the form UUID from each embed URL (the `sibforms.com/forms/view/form/<UUID>` segment). Replace `REPLACE_WITH_EN_FORM_UUID` and `REPLACE_WITH_DE_FORM_UUID` in `hugo.toml`, set `enabled = true`, deploy. Test on `/` and `/de/` in production (CSP/X-Frame-Options must allow `sibforms.com` — Vercel's default headers should be fine, but verify).

3. **Production contact lists not yet created.** Currently only `ai-gov-test-en` (id 3) exists with 2 test contacts. Create `ai-gov-en` and `ai-gov-de` for real subscribers before going live. Keep the test lists for dry-runs.

### Bridge integration (§4 — outside this repo, CT 104)

4. **`bridge.py` Brevo send step not yet wired.** `scripts/build_email.py` in this repo is complete and tested — it reads `public/posts/<slug>/index.html`, extracts `.post-content`, wraps it in the brutalist email template, writes `scripts/email_output.html`. The bridge on CT 104 needs to:
   - After the image push, run `hugo` (or fetch the rendered HTML from Vercel if the bridge doesn't have a local Hugo)
   - Run `python3 scripts/build_email.py posts/<slug>/` to produce the email HTML
   - Read `scripts/email_output.html` and POST it as `htmlContent` to `POST /v3/emailCampaigns`
   - Capture `id` from the 201 response, call `POST /v3/emailCampaigns/<id>/sendNow`
   - Repeat for DE with `docs/<stem>.de.md` → `content/de/posts/<stem>.de.md` → `public/de/posts/<slug>/index.html` → German subject + DE list
   - Failure should be non-blocking (like the image push) — markdown still ships even if the email send fails
   - Required env vars on CT 104: `BREVO_KEY`, `BREVO_EN_LIST_ID`, `BREVO_DE_LIST_ID`, `BREVO_SENDER_EMAIL` (`digest@aigov.philine.ch`)
   - The Brevo API requires a non-default `User-Agent` header (default Python urllib UA is blocked by Cloudflare — use something like `ai-gov-bridge/1.0`)

### Email HTML refinements (post-test observations)

5. **No hero image in email.** Hero PNGs render as broken-image icons in Apple Mail and are silently omitted by Gmail web. Confirmed during test send — removed from `build_email.py`. The title block (orange `#ff4500` box with 4px black border) carries the brutalist aesthetic without images. Do not re-add hero images to email HTML.

6. **`box-shadow` not used in email HTML.** The signature hard offset shadow (`8px 8px 0`) is stripped by Gmail/Outlook. Currently not faked via the table-spacer trick. The 4px black borders + orange accent blocks alone read as "brutalist enough" in an inbox. If the shadow is wanted badly, the table-fake-shadow trick (nested offset cells filled with `#1a1a1a`) can be added later — ~20 extra lines per boxed element.

7. **Dark mode not implemented in email.** The website has `@media (prefers-color-scheme: dark)`. The email HTML is light-mode only. Apple Mail and Gmail dark support `@media (prefers-color-scheme: dark)` in email; Outlook ignores. Low priority — ship light-mode first, add dark mode as a refinement if it looks bad in dark-mode readers.

8. **Brevo free footer ("Sent with Brevo").** Appears on every sent email. Unavoidable on Free. The unsubscribe link Brevo injects is styled with default Brevo CSS, not the brutalist theme — could be overridden with inline CSS on a `[unsubscribe]` merge tag if Brevo allows it. Low priority.

### Brevo account hygiene

9. **Test campaigns can't be deleted.** Brevo doesn't allow deleting sent/scheduled campaigns (403 `permission_denied`). Campaigns 1 + 2 are permanent test records. Ignore them in the dashboard.

10. **Test contacts remain on list 3.** `hendrik.richert@gmail.com` and `philine.richert@gmail.com` are on `ai-gov-test-en` (id 3). Leave them for future dry-runs, or unsubscribe via Brevo dashboard if they should be clean.

11. **Brevo account email is `brevo@richert.li`.** This is the account login email, not the sender email. The sender is `digest@aigov.philine.ch`. The account email doesn't affect sending, but note that `richert.li` DMARC blocks Brevo from sending as that address — don't use `brevo@richert.li` as a campaign sender.

### Documentation updated

12. **AGENTS.md Newsletter section** — added during this session. Documents: ESP, sender, DNS setup, `/sendNow` endpoint, `build_email.py`, DMARC gotcha, CNAME→A record switch, no-hero-image rule, no-handrolled-form rule, `enabled` gate. If the newsletter setup changes, update both AGENTS.md and this section.

## 9. What is NOT in this plan

- No changes to `docs/`, `static/images/`, the transformer, or the upstream research pipeline.
- No GitHub Actions workflow.
- No community Hugo theme.
- No move to `assets/images/`.
- No API key or secret committed to this repo.
