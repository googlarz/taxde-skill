# TaxDE Skill v1.1

TaxDE is a local Claude/Codex skill for German tax optimization, filing preparation, and year-round financial decisions with tax impact. It is the reasoning layer before ELSTER: find deductions, quantify trade-offs, prepare the right numbers, review the Bescheid, and hand off complex cases cleanly when needed.

Version 1.1 turns the repo into a stronger, safer release:

- refreshed README and skill guidance with clearer trust boundaries
- bundled 2024-2026 tax rules and filing deadline helpers
- safer equipment and childcare handling in the calculator flow
- project-scoped profile storage instead of pretending to use shared memory
- a proposal-based updater that checks official BMF sources without silently rewriting the repo

This repo combines:

- the operating prompt in [`SKILL.md`](./SKILL.md)
- shared tax-year logic in [`scripts/tax_rules.py`](./scripts/tax_rules.py)
- refund estimation in [`scripts/refund_calculator.py`](./scripts/refund_calculator.py)
- deadline handling in [`scripts/tax_dates.py`](./scripts/tax_dates.py)
- receipt logging in [`scripts/receipt_logger.py`](./scripts/receipt_logger.py)
- document sorting in [`scripts/document_sorter.py`](./scripts/document_sorter.py)
- project-scoped profile storage in [`scripts/profile_manager.py`](./scripts/profile_manager.py)

Current bundled support is for tax years 2024, 2025, and 2026.

## Why This Repo Exists

Most tax tools are either:

- form fillers that only optimize what the user already knows to mention
- calculators without memory or workflow
- high-trust legal/commercial products that are expensive or overkill for basic planning

TaxDE is built for the gap in between:

- answer the question the user asked
- quantify it with real numbers
- find the next thing they did not know to ask
- keep the reasoning transparent
- stop pretending when the case needs a Steuerberater

## What TaxDE Actually Does

| Workflow | What the user gets | Main backing files |
|----------|--------------------|--------------------|
| Deduction hunt | likely deductions, missing-data gaps, refund estimate | `SKILL.md`, `references/deduction-rules.md`, `scripts/refund_calculator.py` |
| Guided filing | preparation for ELSTER fields and forms | `references/elster-guide.md`, `scripts/tax_dates.py` |
| Scenario modeling | before/after comparison for life or work decisions | `references/scenarios.md`, `scripts/refund_calculator.py` |
| Receipt capture | structured expense logging and deductible treatment | `scripts/receipt_logger.py`, `scripts/tax_rules.py` |
| Document intake | sorted tax folders and missing-document summary | `scripts/document_sorter.py` |
| Bescheid review | plain-language review and Einspruch orientation | `SKILL.md`, `scripts/profile_manager.py` |
| Profile continuity | project-local memory of tax facts and filing history | `scripts/profile_manager.py` |

## What Makes It Trustworthy

- Hard numbers come from scripts, not prompt memory.
- Supported-year thresholds and formulas are centralized instead of duplicated across prompt text.
- Filing deadlines are resolved through code, not hand-written reminder copy.
- Expensive work equipment is treated conservatively and annualized when required.
- The skill explicitly distinguishes:
  - deductible amount
  - reduction in taxable income
  - estimated cash refund
- The repo degrades honestly outside 2024-2026 instead of pretending unsupported years are exact.
- Profile data is project-scoped and does not claim magical cloud memory.
- The skill includes handoff rules for cases that should not be improvised.
- Core behavior is covered by tests.

## Where It Fits

Use TaxDE when you want to reason before filing:

- `What can I deduct?`
- `How much is this actually worth for me?`
- `Should I change anything before year-end?`
- `What does this Steuerbescheid mean?`
- `Which ELSTER fields matter for my case?`

Use ELSTER, WISO, or a Steuerberater when you need:

- formal submission
- product-grade import/export and filing workflows
- licensed professional advice for high-risk or specialist cases

The practical split is simple: TaxDE finds, explains, and prepares; another tool or a professional submits or handles edge-case law.

## How TaxDE Should Behave

The skill is strongest when it follows this response contract:

1. Start with the number, decision, or deadline impact.
2. Show the math in plain language.
3. Label the confidence and the main assumption.
4. Surface one adjacent deduction, risk, or next move if it is genuinely relevant.
5. End with one focused next step instead of generic filler.

Good behavior:

- `Homeoffice: 138 days x EUR 6 = EUR 828 deductible. Likely.`
- `This is a deduction, not EUR 828 cash back. Your refund effect depends on your tax rate.`
- `For 2027 I can only give a fallback estimate unless we verify the current official rules.`

Bad behavior:

- quoting a filing deadline from memory
- treating a deduction amount as the refund amount
- giving unsupported-year numbers as if they were exact
- skipping the handoff when the case is clearly too complex

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

### Develop and verify locally

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall scripts tests
python3 scripts/refund_calculator.py
python3 scripts/receipt_logger.py
python3 scripts/document_sorter.py
```

## Supported Scope

Strong in-repo support:

- employees and common family cases
- homeoffice, commuting, work equipment, training, donations
- childcare and pension contribution orientation
- side income, freelancers, and mixed-income households
- filing preparation and post-assessment review
- life-event modeling across the next 1-3 years

Handled conservatively:

- years outside 2024-2026
- missing-data estimates
- expat or cross-border orientation before specialist review

Mandatory handoff territory:

- US citizenship plus German residency
- complex equity compensation from foreign employers
- 3 or more tax countries in one year
- exit taxation
- high-stakes GmbH structuring or reorganization work

## Accuracy Model

- The repo bundles tax rules. It does not auto-update from official sources.
- For supported years, use the bundled rules and code helpers.
- For `latest`, `current`, `today`, or unsupported years, verify against official sources when available.
- If official verification is not available, the limitation should be stated plainly.
- References in `references/` support reasoning and explanations. They are not a substitute for shared coded constants in `scripts/`.

If this repo ever drifts, update the code first and the copy second.

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

## Optional Dependencies

Core tax logic uses the Python standard library. Document extraction improves if these are installed:

- `pdfplumber`
- `pypdf`
- `Pillow`
- `pytesseract`

OCR also requires a working Tesseract installation on the host machine.

## Repository Layout

```text
taxde-skill/
├── SKILL.md
├── README.md
├── assets/
│   ├── folder_structure_template.md
│   ├── steuerberater_handoff.md
│   └── tax_dashboard_template.html
├── references/
│   ├── deduction-rules.md
│   ├── elster-guide.md
│   ├── expat-guide.md
│   ├── financial-blind-spots.md
│   ├── freelancer-guide.md
│   ├── law-change-monitoring.md
│   ├── life-events.md
│   └── scenarios.md
├── scripts/
│   ├── document_sorter.py
│   ├── profile_manager.py
│   ├── receipt_logger.py
│   ├── refund_calculator.py
│   ├── tax_dates.py
│   └── tax_rules.py
└── tests/
    ├── test_document_sorter.py
    ├── test_refund_calculator.py
    ├── test_tax_dates.py
    └── test_tax_rules.py
```

## Maintainer Rules

When tax law changes or the skill starts drifting, update the repo in this order:

1. `scripts/tax_rules.py`
2. `scripts/tax_dates.py` if filing deadlines changed
3. any affected helper logic in `scripts/`
4. the matching tests in `tests/`
5. the user-facing references in `references/`
6. `SKILL.md` and `README.md`

Maintainer guardrails:

- do not patch numbers in prompt text and forget the code
- do not update references without updating tests for the changed rule
- do not cite unsupported years as exact
- do not silently change the trust model or storage behavior

## Safe Update Pipeline

This repo now includes a proposal-based updater in [`scripts/tax_rule_updater.py`](./scripts/tax_rule_updater.py).

Use it like this:

```bash
python3 scripts/tax_rule_updater.py check
python3 scripts/tax_rule_updater.py draft
python3 scripts/tax_rule_updater.py apply --proposal-dir .taxde-updates/<timestamp>
```

What it does:

- fetches tracked official BMF sources
- extracts supported values for the bundled years
- compares them to `scripts/tax_rules.py` and `scripts/tax_dates.py`
- patches a temporary repo copy, updates the relevant tests and reference table, and runs verification there
- writes a review bundle with `report.md`, `source_snapshot.json`, `proposal.patch`, `verification.log`, and candidate files

What it does not do:

- it does not silently rewrite the repo
- it does not auto-merge anything
- it does not add a fully new supported tax year by magic

That last part is intentional. Adding a new year still needs human review because tariff formulas and year coverage are higher-risk than simple threshold refreshes.

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

The repo should stay useful because the logic, prompt, and docs agree with each other. That is the bar.
