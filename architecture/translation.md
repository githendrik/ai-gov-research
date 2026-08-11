# German translation quality

Status: **applied 2026-08-11** to the Open WebUI automation prompt on CT 104
(automation "AI Governance Weekly Research", `id 134937c8`). First digest that
should reflect it: the run on **Mon 2026-08-17 07:00**.

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

## Task 1 — add the glossary to the Open WebUI prompt (option A) — DONE 2026-08-11

Applied by appending the block below to `data.prompt` of the automation row in
`/opt/open-webui-data/webui.db` on CT 104, after the existing `## Bilingual output`
section. The structural instructions (identical item numbering, verbatim citations,
URLs and `**Source:**`/`**Category:**` lines) were left untouched, since the bridge's
EN/DE parity check depends on them.

Rollback: `/opt/open-webui-data/automation-prompt.bak-20260811.json` holds the
pre-change `data` blob; `/opt/open-webui-data/webui.db.bak-glossary-20260811` is a
full DB backup.

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

## Why the glossary lives in the prompt, not in a Note or Knowledge Base

Investigated 2026-08-11 against the installed Open WebUI (`utils/automations.py`,
`utils/middleware.py`, `utils/tools.py`), because a GUI-editable table would be nicer
than editing a prompt blob.

- **Notes cannot be attached to an automation.** The automation builds its
  `/api/chat/completions` payload by hand (`_run_automation`) with `model`,
  `messages`, `tool_ids`, `features`, `filter_ids`, `terminal_id` — there is no
  `files` key, so the "Attach Notes" path used in normal chats does not exist here.
- **`prompt_template()` supports only user/date variables** (`{{USER_NAME}}`,
  `{{CURRENT_DATE}}`, …). There is no note or KB interpolation.
- **Model-level knowledge is only force-injected in legacy mode.**
  `middleware.py` injects `model.info.meta.knowledge` into `files` only when
  `params.function_calling == 'legacy'`. Under native function calling — the default,
  and what this automation uses — attached knowledge and notes are exposed as *tools*
  (`view_note`, `query_knowledge_files`, …) that the model may or may not call. The
  docs' claim that Full Context (`item.context == 'full'`) is "always injected
  regardless of native function calling" does not match this code path for
  model-attached knowledge.
- Switching the model to `legacy` to force injection would break the digest itself:
  the research phase depends on ~20 rounds of agentic web search, which needs native
  tool calling.

So a Note/KB glossary would be *advisory* — read only if the model chooses to. For a
must-follow rule that is the wrong mechanism. The prompt is the only place in this
version that guarantees the glossary is in context on every run.

If GUI editing becomes important, the workable shape is: keep the glossary in a Note
(nice table, edit any time), and add a small sync step that reads it via
`GET /api/v1/notes/{id}` and rewrites the glossary section of the automation's
`data.prompt` before the weekly run. The note stays the source of truth and the
prompt stays the delivery mechanism.

## Related: the dedup knowledge base was not working (fixed 2026-08-11)

Investigating whether a Note could feed the prompt turned up a live defect in the
dedup path described in `AGENTS.md`.

`model.meta.knowledge` for `ai-gov-research` held a bare ID string
(`["2d9cf10f-…"]`) rather than the knowledge object the frontend writes.
`utils/tools.py::get_attached_knowledge()` skips non-dict entries
(`if not isinstance(item, dict): continue`), so the `<attached_knowledge>` system
message was never emitted and the KB was invisible to the model — not merely
optional. (The legacy-mode path at `middleware.py:2479` calls `item.get(...)` on the
same entry and would raise `AttributeError`; it never ran because the model uses
native function calling.) Separately, nothing in the automation prompt ever told the
model to consult the KB.

Both fixed: the attachment was rewritten as the full knowledge dict plus
`type: "collection"`, and a dedup step was added to the prompt's research process
instructing the model to call `query_knowledge_files` / `grep_knowledge_files` for
each candidate item before writing. Verified by calling `get_attached_knowledge()`
against the stored meta: 0 advertised items before, 1 after.

This remains an *instruction*, not a guarantee — under native function calling the
model still chooses whether to call the tools. The deterministic alternative, if
duplicates keep appearing, is to have `bridge.py` extract recent item headings from
`docs/*.md` and rewrite an "Already covered" section of `data.prompt` before each
run, putting the titles in context with no tool call required.

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
