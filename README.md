# TaxDE Skill v1.1

**German tax copilot for people who need more than a filing wizard.**

TaxDE is a local Claude/Codex skill for German tax optimization, filing preparation, document triage, decision support, and post-filing review. It is built for the part normal tax apps rarely handle well: reasoning across your whole situation, showing the math, and telling you what matters next.

If Taxfix-style tools are good at interview flows, TaxDE is good at everything around the flow:

- finding deductions you did not know to ask about
- modeling decisions before you make them
- telling you what documents are missing
- reviewing a Steuerbescheid after it arrives
- preparing a clean handoff when a Steuerberater is the right move

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
| Home office, commute, equipment | calculates the deduction logic and shows the formula | helps users understand what is deductible versus what only reduces taxable income |
| Marriage, baby, side income, moving | models tax impact this year and next year | useful before life changes turn into tax surprises |
| Salary package or freelance offer | compares net outcomes, benefits, and tax effect | decision support, not just filing support |
| Messy tax folder | sorts documents, classifies likely categories, identifies gaps | saves time before filing even starts |
| Steuerbescheid arrived | explains what changed and whether a challenge is worth exploring | post-filing value that filing apps usually stop short of |
| Complex international or equity case | prepares a structured Steuerberater brief | saves paid adviser time instead of sending the user in blind |

## What Builds Confidence

TaxDE is designed to earn trust in boring, practical ways:

- **Hard numbers come from code**: bundled rules live in [`scripts/tax_rules.py`](./scripts/tax_rules.py), not only in prompt text.
- **Deadlines come from code**: filing dates live in [`scripts/tax_dates.py`](./scripts/tax_dates.py), not memory.
- **Unsupported years are explicit**: the repo supports 2024, 2025, and 2026 and degrades honestly outside that range.
- **Deductions are labeled correctly**: the skill distinguishes deductible amount, taxable-income reduction, and estimated cash refund.
- **Equipment handling is conservative**: expensive work equipment is annualized when required instead of being fully expensed by mistake.
- **Profile storage is local to the project**: no fake shared memory claims; structured data lives in `.taxde/taxde_profile.json`.
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

### Use it as a skill

1. Clone the repository.
2. Load or symlink the repo into your local skill setup.
3. Start with prompts like these in German or English:

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
- write a review bundle with patch, source snapshot, and candidate files

That means TaxDE can stay current without pretending an autonomous rule rewrite is safe.

## Privacy and Storage

TaxDE stores structured facts in `.taxde/taxde_profile.json` inside the active project.

Stored:

- tax profile facts
- filing history
- current-year receipts
- relevant notes tied to the user's tax situation

Not stored in the profile JSON:

- raw document bodies
- bank credentials
- passwords
- identity documents

Older installs may still read `~/.claude/projects/taxde_profile.json` as a legacy fallback.

## Repository Map

This repo combines prompt logic, deterministic helpers, references, and assets:

- [`SKILL.md`](./SKILL.md): operating prompt for the skill
- [`scripts/tax_rules.py`](./scripts/tax_rules.py): bundled year-specific rules
- [`scripts/refund_calculator.py`](./scripts/refund_calculator.py): refund and confidence logic
- [`scripts/tax_dates.py`](./scripts/tax_dates.py): filing deadlines
- [`scripts/receipt_logger.py`](./scripts/receipt_logger.py): structured receipt capture
- [`scripts/document_sorter.py`](./scripts/document_sorter.py): folder sorting and document classification
- [`scripts/profile_manager.py`](./scripts/profile_manager.py): project-scoped profile storage
- [`scripts/tax_rule_updater.py`](./scripts/tax_rule_updater.py): safe update proposal pipeline
- [`references/`](./references): deduction, filing, life-event, scenario, and law-change guides
- [`assets/`](./assets): dashboard template and handoff assets
- [`tests/`](./tests): regression coverage for the core helpers

## Verification

Recommended verification before merging:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall scripts tests
python3 scripts/refund_calculator.py
python3 scripts/receipt_logger.py
python3 scripts/document_sorter.py
python3 scripts/tax_rule_updater.py check
```

## What Comes Next

If you want the north-star version of this product, see [ROADMAP.md](./ROADMAP.md).

That plan turns TaxDE from a strong skill into a true tax workspace with:

- claim objects
- evidence tracking
- filing readiness
- document coverage
- source provenance
- richer Bescheid and scenario support

That is the direction that makes TaxDE feel less like a clever chat and more like the best tax product a user has ever worked with.
