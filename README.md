# TaxDE Skill

**German tax copilot for people who need more than a filing wizard.**

TaxDE is a local Claude/Codex skill for German tax optimization, filing preparation, document triage, decision support, and post-filing review. It is built for the part normal tax apps rarely handle well: reasoning across your whole situation, showing the math, telling you what matters next, and now keeping that work in a project-local tax workspace.

If Taxfix-style tools are good at interview flows, TaxDE is good at everything around the flow:

- finding deductions you did not know to ask about
- modeling decisions before you make them
- telling you what documents are missing
- tracking which claims are confirmed, estimated, or still blocked on evidence
- building filing packs instead of leaving everything trapped in chat history
- reviewing a Steuerbescheid after it arrives
- preparing a clean handoff when a Steuerberater is the right move

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/googlarz/taxde-skill.git
cd taxde-skill
```

### 2. Install Python dependencies

The core logic works on the standard library, but document extraction and OCR are better with the optional Python packages:

```bash
python3 -m pip install -r requirements.txt
```

### 3. Install optional system tools for OCR and scanned PDFs

If you want image OCR and scanned-PDF extraction to work well, install:

- `tesseract`
- `poppler`

Examples:

```bash
brew install tesseract poppler
```

or on Debian/Ubuntu:

```bash
sudo apt-get install tesseract-ocr poppler-utils
```

### 4. Load it as a local skill

Symlink the repo into your local skill directory, for example:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -s "$PWD" "${CODEX_HOME:-$HOME/.codex}/skills/taxde"
```

If your setup uses a different skill path, load or symlink the repo there instead.

## Why It Feels Different

Most tax software helps only once you are already inside a filing flow.

TaxDE is meant to help:

- **before filing**: `Should I buy this laptop now or in January?`
- **during filing**: `What belongs in Anlage N, and what is still missing?`
- **after filing**: `Why did the Finanzamt reject this, and is an Einspruch worth it?`
- **between tax years**: `What should I still do before December 31?`

That makes it much more useful than a form-only app for people with real decisions, messy documents, or anything outside a vanilla employee case.

## What TaxDE Can Support Today

| Situation | What TaxDE does | Why people use it |
|----------|------------------|-------------------|
| Starting a return | runs a deduction hunt, estimates refund, flags missing inputs | better than waiting for a wizard to ask the right question |
| Tax workspace | builds claims, readiness, evidence coverage, and next tasks for the active year | gives the user a persistent working state instead of a one-off chat answer |
| Annual timeline | shows the current tax phase, next deadline, and seasonal actions | keeps the product useful all year instead of only at filing time |
| Home office, commute, equipment | calculates the deduction logic and shows the formula | helps users understand what is deductible versus what only reduces taxable income |
| Marriage, baby, side income, moving | models tax impact this year and next year | useful before life changes turn into tax surprises |
| Salary package or freelance offer | compares net outcomes, benefits, and tax effect | decision support, not just filing support |
| Messy tax folder | sorts documents, classifies likely categories, identifies gaps | saves time before filing even starts |
| Filing prep pack | builds a form-oriented pack with claims, missing docs, and next steps | helps users move into ELSTER or WISO faster |
| Steuerbescheid arrived | explains what changed and whether a challenge is worth exploring | post-filing value that filing apps usually stop short of |
| Structured deliverables | builds yearly summaries, claim checklists, missing-doc checklists, and year-end action lists | turns chat into reusable work product |
| Complex international or equity case | prepares a structured Steuerberater brief | saves paid adviser time instead of sending the user in blind |

## What Builds Confidence

TaxDE is designed to earn trust in boring, practical ways:

- **Hard numbers come from code**: bundled rules live in [`scripts/tax_rules.py`](./scripts/tax_rules.py), not only in prompt text.
- **Critical rules have provenance**: [`scripts/rule_registry.py`](./scripts/rule_registry.py) exposes source metadata, freshness state, and deadline provenance.
- **Deadlines come from code**: filing dates live in [`scripts/tax_dates.py`](./scripts/tax_dates.py), not memory.
- **Unsupported years are explicit**: the repo supports 2024, 2025, and 2026 and degrades honestly outside that range.
- **Deductions are labeled correctly**: the skill distinguishes deductible amount, taxable-income reduction, and estimated cash refund.
- **Equipment handling is conservative**: expensive work equipment is annualized when required instead of being fully expensed by mistake.
- **Profile storage is local to the project**: no fake shared memory claims; structured data lives in `.taxde/taxde_profile.json`.
- **Claims and readiness are persisted**: TaxDE writes project-local claims, filing packs, workspaces, and source snapshots under `.taxde/`.
- **Seasonal guidance is built in**: TaxDE keeps an annual timeline so January, filing season, Bescheid season, and year-end work are treated differently.
- **Structured outputs exist outside chat**: TaxDE can build a yearly summary, claim checklist, missing-document checklist, filing pack, Bescheid review pack, and adviser briefing.
- **Updates are reviewable**: the repo includes a safe updater that checks official sources and drafts a patch instead of silently rewriting tax logic.
- **Core paths are tested**: refund logic, deadlines, document sorting, and updater behavior all have regression tests.

## How TaxDE Thinks

The intended interaction model is simple:

1. lead with the money, decision, or deadline impact
2. show the math in plain language
3. state what is confirmed versus estimated
4. surface the next highest-value thing the user should do
5. stop and hand off when the case becomes specialist territory

Good output from TaxDE should feel like this:

- `Homeoffice: 138 days x EUR 6 = EUR 828 deductible.`
- `This is a deduction, not EUR 828 cash back. The refund effect depends on your tax rate.`
- `Your 2025 filing is probably missing childcare evidence. That is the biggest remaining gap.`

## Quick Start

Start with prompts like these in German or English:

```text
Ich will meine Steuererklaerung fuer 2025 vorbereiten.
Was kann ich fuer Homeoffice, Pendeln und meinen Laptop absetzen?
Wir bekommen ein Baby. Was aendert sich steuerlich dieses Jahr und naechstes Jahr?
Bitte erklaere mir meinen Steuerbescheid.
Bitte sortiere meinen Steuerordner und sag mir, was fehlt.

I want to prepare my 2025 German tax return.
What can I deduct for working from home, commuting, and my laptop?
We're having a baby. What changes tax-wise this year and next year?
Please explain my German tax assessment notice.
Please sort my tax documents and tell me what is missing.
```

## Practical Prompts People Actually Use

These are the prompts that make TaxDE more compelling than a standard filing app.

### Year-end money moves

- `Should I buy my work laptop in December or January if I want the deduction in this tax year?`
- `I already logged 160 home-office days. What should I still do before year-end to lower tax?`

### Life events and household planning

- `We're getting married in August. Should we change tax classes, and what changes this year versus next year?`
- `We're expecting a baby. Model Kindergeld, childcare deductions, and whether a tax-class change could improve Elterngeld.`

### Job and income decisions

- `Compare EUR 78k salary versus EUR 74k plus company car, Jobticket, and bAV. Which leaves me better off net?`
- `If I switch from employment to freelance work, what day rate do I need to match my current net income?`

### Bescheid review

- `Translate this Steuerbescheid into plain English and tell me whether an Einspruch is worth it.`
- `The tax office rejected part of my home-office claim. What is the likely reason, and what evidence would help?`

### Receipts and documents

- `I bought a monitor, desk, and headset. Log them and tell me what is immediately deductible versus annualized.`
- `Sort this folder of tax documents and tell me what is missing before I start filing.`

### Complex-case handoff

- `I have RSUs from a US employer and moved to Germany mid-year. Prepare a Steuerberater briefing with the questions I should ask.`
- `I worked in Germany, Poland, and the UK in the same year. What can you prepare before I talk to a tax adviser?`

## Where It Is Strongest

TaxDE is strongest for:

- employees and common family cases
- home office, commuting, work equipment, training, donations
- childcare and pension contribution orientation
- side income, freelancers, and mixed-income households
- claim tracking, readiness scoring, and missing-document triage
- filing pack generation for ELSTER / WISO preparation
- Bescheid diffing against what was expected
- salary package and freelance break-even scenarios
- filing preparation and post-assessment review
- life-event modeling across the next 1-3 years

## Where It Is Deliberately Conservative

TaxDE will help orient and prepare, but it should not bluff in:

- years outside 2024-2026 without official verification
- missing-data-heavy estimates
- expat or cross-border questions before specialist review
- complex equity compensation
- US citizenship plus German residency
- exit taxation
- high-stakes GmbH structuring or reorganization work

In those cases the right behavior is not `sorry, ask someone else`. The right behavior is `here is the exact brief, evidence, and question list to take to a Steuerberater`.

## How It Stays Current

This repo does **not** auto-update itself blindly.

Instead, it uses a safer model:

- bundled rules for supported years
- explicit official-source checks for `current`, `latest`, `today`, or unsupported years
- a proposal-based updater in [`scripts/tax_rule_updater.py`](./scripts/tax_rule_updater.py)

The updater can:

- fetch tracked official BMF sources
- compare them to the bundled rules
- patch a temporary repo copy
- update matching tests and the reference table
- run verification
- write a review bundle with patch, source snapshot, change classifications, release notes, and candidate files
- require explicit reviewer approval before apply

That means TaxDE can stay current without pretending an autonomous rule rewrite is safe.

## Privacy and Storage

TaxDE keeps its working state inside the active project's `.taxde/` directory.

Typical files now include:

- `.taxde/taxde_profile.json`
- `.taxde/claims/<tax-year>.json`
- `.taxde/workspace/<tax-year>.json`
- `.taxde/workspace/<tax-year>-filing-pack.json`
- `.taxde/workspace/<tax-year>-outputs.json`
- `.taxde/source_snapshots/*.json`

Stored:

- tax profile facts
- filing history
- current-year receipts
- claims and readiness state
- filing-pack output
- archived official-source snapshots

Not stored in the profile JSON:

- raw document bodies
- bank credentials
- passwords
- identity documents

Older installs may still read `~/.claude/projects/taxde_profile.json` as a legacy fallback.

## Repository Map

This repo combines prompt logic, deterministic helpers, references, and assets:

- [`SKILL.md`](./SKILL.md): operating prompt for the skill
- [`scripts/taxde_storage.py`](./scripts/taxde_storage.py): project-local storage for profile, claims, workspace, packs, and source snapshots
- [`scripts/tax_rules.py`](./scripts/tax_rules.py): bundled year-specific rules
- [`scripts/rule_registry.py`](./scripts/rule_registry.py): rule values plus provenance and freshness metadata
- [`scripts/refund_calculator.py`](./scripts/refund_calculator.py): refund and confidence logic
- [`scripts/tax_dates.py`](./scripts/tax_dates.py): filing deadlines
- [`scripts/claim_engine.py`](./scripts/claim_engine.py): first-class claim generation and persistence
- [`scripts/workspace_builder.py`](./scripts/workspace_builder.py): readiness, evidence coverage, and year workspace
- [`scripts/tax_timeline.py`](./scripts/tax_timeline.py): annual tax timeline and seasonal action planner
- [`scripts/document_coverage.py`](./scripts/document_coverage.py): expected-vs-present document tracking
- [`scripts/filing_pack.py`](./scripts/filing_pack.py): ELSTER / WISO preparation pack output
- [`scripts/bescheid_diff.py`](./scripts/bescheid_diff.py): expected-vs-assessed review helper
- [`scripts/scenario_engine.py`](./scripts/scenario_engine.py): package comparison and freelance break-even analysis
- [`scripts/adviser_handoff.py`](./scripts/adviser_handoff.py): specialist handoff trigger and briefing packet
- [`scripts/output_builder.py`](./scripts/output_builder.py): yearly summary, checklist, review pack, and action-list output suite
- [`scripts/receipt_logger.py`](./scripts/receipt_logger.py): structured receipt capture
- [`scripts/document_sorter.py`](./scripts/document_sorter.py): folder sorting and document classification
- [`scripts/profile_manager.py`](./scripts/profile_manager.py): project-scoped profile storage
- [`scripts/tax_rule_updater.py`](./scripts/tax_rule_updater.py): safe update proposal pipeline
- [`scripts/update_sources.py`](./scripts/update_sources.py): official-source snapshot archiving
- [`references/`](./references): deduction, filing, life-event, scenario, and law-change guides
- [`assets/`](./assets): dashboard template and handoff assets
- [`tests/`](./tests): regression coverage for the core helpers

## Verification

Recommended verification before merging:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall scripts tests
python3 scripts/refund_calculator.py
python3 scripts/claim_engine.py
python3 scripts/workspace_builder.py
python3 scripts/tax_timeline.py
python3 scripts/filing_pack.py
python3 scripts/output_builder.py
python3 scripts/adviser_handoff.py
python3 scripts/receipt_logger.py
python3 scripts/document_sorter.py
python3 scripts/tax_rule_updater.py check
```
