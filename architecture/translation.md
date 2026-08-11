# German translation quality

Status: **pending — not yet applied.** Written 2026-08-11.

The DE half of each digest is produced in the same generation pass as the EN half
(single prompt, split on `---DE---` by `bridge.py` on homelab CT 104). There is no
separate translation step and no repo-side transformation of the German text — so
every fix below is a change to the Open WebUI system prompt on CT 104, not to this
repo.

## Why

Review of `docs/2026-08-04-ai-governance.de.md` and `docs/2026-08-10-ai-governance.de.md`
against their EN sources found four recurring problems:

1. **False friends** — `unsanktionierte Aktionen` (unsanktioniert = *unpunished*),
   `materieller Schaden` (= property damage), `prozessierbar`, `regulatorische
   Übernahme`, `Verleger` for a news site operator.
2. **Calques** — `Eindämmung` for containment, `Bedrohungsoberfläche` for attack
   surface, `adressieren` for *to address*, `hartes Recht` for hard law,
   `Abtrünnige KI` for rogue AI.
3. **Invented compounds** — `Durchsetzungsmeilenstein`, `Fehlcompliance`,
   `Compliance-Zeithorizont`, `Nahzeit-Entwicklung`, `Dritt-Evaluierer`.
4. **Inconsistency** — ß in the 08-04 issue vs ss in 08-10; `5.000` vs `750'000`;
   `Evaluierung vor Markteintritt` vs `Pre-Market-Evaluation` inside one item.

Audience and sources are Swiss (`aigov.philine.ch`, `.ch` sources, SearXNG on
`de-CH`), so Swiss orthography is the target.

## Task 1 — add the glossary to the Open WebUI prompt (option A)

Requires SSH to CT 104 / the Open WebUI admin UI.

1. Open the model's system prompt for the "AI Governance Research" automation.
2. Append the block below to the section that instructs the model to emit the DE
   half after `---DE---`. Do not replace the existing structural instructions
   (identical item numbering, citations and URLs must stay untouched — the bridge's
   parity check depends on it).
3. Trigger one manual run, diff the resulting `docs/*.de.md` against the rules, and
   note the result in a `daily-log/` entry.

```
GERMAN STYLE RULES

Write German as a Swiss tech/policy journalist would — not as a translation.
Prefer a natural rephrasing over a literal one. Never invent noun compounds:
if a compound is not attested in German media, use a prepositional phrase
instead (e.g. "Meilenstein bei der Durchsetzung", not
"Durchsetzungsmeilenstein"; "Technologien zum Herkunftsnachweis", not
"Herkunftstechnologien").

Orthography and numbers: Swiss German. Never use ß — always ss
(Bussgeld, grosse, einschliesslich, Massnahmen). Thousands separator is an
apostrophe (750'000), not a period. Write 5000, 15 Mio. €, 30 Mrd. €.

Keep these terms in English, do not translate them:
AI Act, AI Office, Governance, Compliance, Framework/Frameworks, Benchmark,
Sandbox, Frontier, Open Weights, Incident Response, Regulatory Capture,
Rogue, Kill Switch, Prompt, Audit, Preparedness Framework.

Never use the term on the left; use the right instead:
  Rahmenwerk / Rahmenwerke        -> Framework / Frameworks
  unsanktioniert                  -> nicht autorisiert
  Eindämmung (= containment)      -> Testumgebung / Containment
  Bedrohungsoberfläche            -> Angriffsfläche
  Abtrünnige KI                   -> Rogue-KI
  adressieren (= to address)      -> behandeln / regeln
  hartes Recht                    -> verbindliches Recht
  Regulatoren                     -> Aufsichtsbehörden
  Transparenzverpflichtungen      -> Transparenzpflichten
  Kontrollen (= controls)         -> Kontrollmechanismen / Massnahmen
  materieller Schaden (= harm)    -> nennenswerter Schaden
  Präzedenzbeispiel               -> Präzedenzfall
  Dritt-Evaluierer / -Evaluierung -> unabhängige Prüfstellen
  prozessierbar                   -> einklagbar / justiziabel
  regulatorische Übernahme        -> regulatorische Vereinnahmung
  Rückschau (= postmortem)        -> Nachanalyse / Post-Mortem
  Agenten-Spuren                  -> Agenten-Logs
  Verleger (= news publisher)     -> Betreiber der Website
  studiert (= is being studied)   -> geprüft / herangezogen
  warnende Lektion                -> Warnsignal / mahnendes Beispiel
  Fehlcompliance                  -> fehlerhafte Umsetzung
  Sandbox-Fluchten                -> Ausbrüche aus der Sandbox
  Lückenfüller                    -> springen in die Lücke

Use one rendering per term throughout a digest. Do not alternate between
e.g. "Evaluierung vor Markteintritt" and "Pre-Market-Evaluation", or
between "Evaluierungskapazität" and "Evaluierungskompetenz".
```

## Task 2 — document the DE pipeline upstream

`AGENTS.md` in this repo points at "§15" of
`Homelab/reference/gmktec-m6-local-llm-guide.md` for the pipeline, but that guide
ends at §14 and says nothing about the EN+DE generation or the `---DE---` split.
Add the missing section, including a pointer back to this file for the glossary.

## Task 3 (later, optional) — enforce the glossary

Prompt-only enforcement drifts silently. If that becomes a problem, add the check
to `bridge.py` next to the existing EN/DE structural parity check — **non-blocking**:
report on a hit, push anyway.

Do **not** make this fail the Vercel build. The pipeline is unattended (generation
Mon 07:00, push Mon 07:30); a build-failing lint would silently drop a week's digest
over a word choice, and there is nothing editable to fix — `docs/*.de.md` is
regenerated upstream and `content/de/posts/` is generated from it.

If the check is added, keep the glossary in one machine-readable file in this repo
(e.g. `de-glossary.toml`) and have both the bridge check and the pasted prompt block
derive from it, so they cannot diverge.

## Open decisions

- **Field labels.** `**Source:**`, `**URL:**`, `**Category:**`, `**Summary:**`,
  `**Why it matters:**` and the category values (`Regulation`, `Audit`, `Industry`)
  stay English in the DE posts — the most visible non-native artifact for a German
  reader. Nothing in `layouts/` or `themes/` matches those strings, and `i18n/de.yaml`
  exists, so translating them is safe on the Hugo side. Check `bridge.py`'s parity
  check and `scripts/build_email.py` before flipping it.
- **`Frontier-Labor`.** Literally a room. `KI-Labor` is used by German media, so it
  is defensible; `führende KI-Unternehmen` reads better.
