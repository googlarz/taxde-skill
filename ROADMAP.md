# TaxDE v2 Roadmap

This document defines the next major version of TaxDE.

The goal is not to make the current skill slightly nicer. The goal is to make TaxDE feel like the best tax product a user has ever worked with: fast, trustworthy, proactive, up to date, and materially useful outside a once-a-year filing flow.

## North Star

TaxDE v2 should be:

- the most trusted German tax copilot for planning, preparation, and review
- useful all year, not just during filing season
- explicit about what it knows, what it inferred, and what still needs evidence
- faster than manual tax prep and smarter than a form wizard
- conservative enough to trust with money decisions

## The Ideal User Experience

The user should feel like they are working with a sharp tax operator, not a chatbot.

### 1. Start from a tax workspace, not a blank chat

When a user opens TaxDE, they should see a living workspace for the active tax year:

- projected refund or likely payment
- readiness score
- missing documents checklist
- top deduction opportunities
- next deadline
- recent receipts and open tasks

The chat becomes the control surface for the workspace, not the whole product.

### 2. Every claim should have evidence, status, and next steps

Instead of a loose list of deductions, users should get claim cards:

- amount or range
- confidence level
- legal basis or source basis
- evidence already on file
- evidence still needed
- likely refund effect
- recommended next action

This turns tax advice into a workflow the user can trust and complete.

### 3. TaxDE should save time, not just explain things

The product should actively reduce effort:

- auto-sort documents
- extract key values
- detect what is missing
- pre-build ELSTER-ready summaries
- pre-fill claim checklists
- generate Bescheid review notes
- prepare Steuerberater handoff packs

### 4. TaxDE should help with decisions before they become tax problems

This is where TaxDE can beat filing apps:

- salary package comparisons
- company car vs cash
- freelance break-even analysis
- marriage and tax-class timing
- baby / childcare planning
- year-end deduction timing
- relocation and side-income decisions

### 5. TaxDE should be visibly up to date

Users should not have to wonder whether the numbers are stale.

TaxDE v2 should show:

- rule year in use
- last verified date
- source provenance for critical figures
- warning when a year is unsupported or pending verification

## Product Principles

### 1. Reliability beats breadth

It is better to be correct and narrow than broad and sloppy.

### 2. Workflow beats pure conversation

A great chat reply is not enough. The user needs persistent structure: claims, evidence, deadlines, missing items, and next actions.

### 3. Evidence beats assertion

Every meaningful number should come from one of:

- bundled deterministic rules
- extracted user documents
- explicit user input
- verified official sources

### 4. Unknown is better than wrong

TaxDE should say:

- exact
- estimated
- unsupported
- needs verification

It should never hide uncertainty behind polished prose.

### 5. Planning beats filing-only utility

The product should help before, during, and after filing:

- before: decisions and timing
- during: preparation and submission support
- after: Bescheid review and next-year learning

## What v2 Must Add

## 1. Claim Engine

Introduce a first-class `claim` object for each deduction or tax opportunity.

Each claim should contain:

- `id`
- `tax_year`
- `category`
- `title`
- `status` such as `detected`, `needs_evidence`, `ready`, `submitted`, `rejected`
- `amount_deductible`
- `estimated_refund_effect`
- `confidence`
- `legal_basis`
- `source_of_truth`
- `evidence_present`
- `evidence_missing`
- `next_action`

This becomes the backbone of the product.

## 2. Readiness and Coverage Model

Build a year-level readiness model instead of a generic refund number alone.

The workspace should answer:

- how ready is this return
- what is missing
- what is blocked on documents
- what is estimated vs confirmed
- where the biggest money is still unclaimed

Example top-level metrics:

- filing readiness %
- evidence coverage %
- refund confidence %
- money-left-on-table estimate

## 3. Document Coverage Map

Document handling should move from folder sorting to filing support.

For each return, TaxDE should know:

- expected document types for this profile
- which ones are present
- which are partial
- which extracted fields are still missing

This should produce a practical checklist like:

- `Lohnsteuerbescheinigung`: present
- `Kita annual statement`: missing
- `Rürup statement`: present but contribution field not extracted

## 4. Rules Registry with Provenance

Turn bundled constants into a rules registry, not just a Python dict.

Each tracked rule should have:

- value
- year
- source URL
- source title
- verified date
- verification method
- confidence or freshness state

This enables:

- freshness banners
- auditability
- better updater diffs
- safer release notes

## 5. Better Update System

The new updater is a good base, but v2 needs a full update workflow:

- source adapters per official source
- normalized extracted rule schema
- source snapshot archive
- change classification
- required reviewer approval
- regression tests before apply
- release note generation when rules change

The updater should support:

- threshold changes
- tariff parameter changes
- deadline changes
- social-contribution-linked limits
- explicit unsupported-source warnings

## 6. Bescheid Diff Engine

This should become a first-class feature.

Given:

- prepared claims
- expected filing values
- received Bescheid

TaxDE should output:

- accepted claims
- reduced claims
- rejected claims
- likely reason
- whether an Einspruch looks worthwhile
- draft response and supporting evidence list

## 7. Scenario Workbench

Scenario support should move from prompt templates to a repeatable engine.

Users should be able to compare:

- baseline
- option A
- option B
- tax effect
- social contribution effect
- net cash effect
- one-year and multi-year effect

This is where TaxDE becomes much more useful than Taxfix.

## 8. Annual Tax Timeline

TaxDE should behave like a year-round advisor:

- January: document and law-change check
- February to July: filing preparation
- August to October: Bescheid review
- November to December: year-end optimization sprint

This should be built into the product instead of being just prompt guidance.

## 9. Better Outputs

v2 should produce structured deliverables, not only chat answers:

- yearly tax summary
- claim checklist
- missing-doc checklist
- filing pack for ELSTER or WISO
- Bescheid review pack
- Steuerberater briefing
- year-end action list

## Reliability Model for v2

To approach "100% reliable" in practice, TaxDE needs layered reliability, not blind confidence.

### Layer 1. Deterministic tax logic

- shared rule registry
- deterministic calculators
- explicit year handling
- no hidden fallback without warning

### Layer 2. Source-backed freshness

- official-source links for tracked values
- last verified date
- freshness status
- updater proposals with review

### Layer 3. Evidence-backed user state

- structured profile
- structured receipts
- structured claims
- document coverage map

### Layer 4. Product-level validation

- unit tests for rules and calculators
- golden tests for user journeys
- fixture-based tests for update extraction
- regression tests for document sorting and claim generation

### Layer 5. Safe handoff

When TaxDE should stop, it should stop cleanly and helpfully:

- specialist handoff trigger
- handoff packet
- exact questions to ask
- evidence package ready

## Proposed Architecture Changes

## 1. New data model

Add project-local structured artifacts:

- `.taxde/profile.json`
- `.taxde/claims/<tax-year>.json`
- `.taxde/workspace/<tax-year>.json`
- `.taxde/source_snapshots/`
- `.taxde/proposals/`

## 2. New modules

Likely additions:

- `scripts/claim_engine.py`
- `scripts/workspace_builder.py`
- `scripts/document_coverage.py`
- `scripts/rule_registry.py`
- `scripts/bescheid_diff.py`
- `scripts/scenario_engine.py`
- `scripts/update_sources.py`

## 3. Clear separation of concerns

- rules and formulas
- user state
- claim generation
- document extraction
- filing workflow
- updater and provenance
- output rendering

## What Users Should Be Able To Say

If v2 is good, people will use prompts like these naturally:

- `What am I still missing before I file?`
- `Show me which deductions are confirmed versus still estimated.`
- `If I buy this laptop in December, what changes this year versus next year?`
- `Compare my current salary package with a freelance offer at EUR 650 per day.`
- `Review this tax office letter and tell me exactly what changed from what we expected.`
- `Build me a filing pack I can copy into ELSTER.`
- `What is the single highest-value thing I should still do this month?`
- `Prepare the documents and open questions for my tax adviser.`

That is the bar: practical, decision-oriented, time-saving, and trustworthy.

## Delivery Plan

## Phase 1. Trust Foundation

Goal:

- make rules, freshness, and evidence explicit

Build:

- rule registry with provenance
- source freshness metadata
- claim object model
- workspace skeleton

Success criteria:

- every high-signal number has provenance
- every claim can say whether it is confirmed or estimated

## Phase 2. Workflow Engine

Goal:

- move from chat-only help to tax workflow

Build:

- readiness score
- claim list generation
- missing-doc checklist
- tax-year workspace summary

Success criteria:

- user can open a project and know what is done, what is missing, and what matters most

## Phase 3. Document and Filing Intelligence

Goal:

- materially reduce filing effort

Build:

- document coverage model
- extracted field tracking
- filing pack output
- improved ELSTER guidance based on actual available evidence

Success criteria:

- user can move from messy folder to filing-ready checklist quickly

## Phase 4. Bescheid and Scenario Power

Goal:

- make TaxDE genuinely better than filing-only tools

Build:

- Bescheid diff engine
- Einspruch guidance pack
- scenario workbench
- multi-year planning outputs

Success criteria:

- users use TaxDE for decisions and post-filing review, not just prep

## Phase 5. Updater and Release Hardening

Goal:

- keep the product current and auditable

Build:

- richer updater source adapters
- snapshot archive
- change severity classification
- release note generation
- golden journey tests

Success criteria:

- rule updates become a repeatable release process instead of ad hoc maintenance

## Immediate Next Build Steps

If work starts now, the best order is:

1. Add a rule registry layer with provenance fields.
2. Introduce a claim model and workspace JSON.
3. Generate a first filing-readiness view from current profile and receipts.
4. Add document coverage tracking on top of the sorter.
5. Build a simple filing pack output.

This sequence gives the biggest user-visible jump in usefulness without compromising reliability.

## Anti-Goals

Do not make v2:

- a legal-advice bot pretending certainty
- a generic finance assistant with tax flavor
- a pure filing wizard clone
- a fully autonomous updater that silently edits rules
- a beautiful dashboard with weak provenance underneath

## Final Standard

TaxDE v2 should make the user think:

- `It already understands my situation.`
- `It tells me what matters most.`
- `It shows me which numbers are solid and which still need proof.`
- `It saves me time instead of creating more work.`
- `I would trust this before I trust a generic tax app interview.`

That is the version worth building.
