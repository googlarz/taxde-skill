# TaxDE Skill

**The financial advisor the German middle class never had access to.**

TaxDE Skill is a Claude Code skill that turns every tax conversation into a guided optimization session — with a live visual dashboard rendered as a Claude artifact alongside the chat.

---

## What it does

Most Germans leave €500–€2,000 on the table every year. TaxDE Skill fixes that.

It goes beyond filling in ELSTER fields. It hunts for deductions you didn't know existed, models scenarios before you make life decisions, flags law changes before they cost you money, and hands you off to a Steuerberater with a full briefing — not just "see a professional."

**8 operating modes**, detected automatically from context:

| Mode | Triggered by |
|------|-------------|
| Year-Round Advisor | Any tax question, any time |
| Deduction Hunter | "What can I claim?" / start of filing season |
| Scenario Simulator | "What if I…" / life decisions |
| Guided Filing | "Help me file" / ELSTER walkthrough |
| Post-Assessment Review | Steuerbescheid arrives |
| Receipt Capture | Ongoing expense logging |
| Financial Blind Spot Scanner | Insurance, investments, fees |
| Life Transition Intelligence | Baby, marriage, new job, moving |

---

## Artifact + Chat

Every session uses both panels:

- **Chat** — TaxDE Skill explains, empathizes, asks questions, celebrates wins ("That's €840 you would have missed")
- **Artifact** — A live HTML tax dashboard: estimated refund, itemized deductions with confidence signals, countdown to Abgabefrist, personalized tips. Regenerates whenever meaningful new data arrives.

---

## How it compares

Each tool has a different job. Here's an honest breakdown:

**ELSTER** (free, official)
The authoritative source — direct submission, legally binding, no cost. But purely a form interface: no guidance, no deduction suggestions, no explanations. You need to know what you're doing. TaxDE Skill is designed to prepare you for ELSTER, not replace it.

**Taxfix / SteuerGo** (€30–50/year)
Fast, mobile-friendly, genuinely good for straightforward employed cases. Interview-style flow covers the main deductions. Where they fall short: the questions only go as deep as you answer. If you don't know homeoffice is claimable, they won't find it. No year-round use, no "what if" modeling, no life event strategy.

**WISO Steuer** (€30–50/year)
The most capable traditional tax app — handles complex situations, has scenario tools, updates annually for law changes, good document import. Solid choice for anyone who wants a proven, licensed product. Limitation: still form-centric. It optimizes *within* what you tell it; it doesn't proactively reason about your whole financial situation.

**TaxDE Skill** (free, runs in Claude Code)
Not a replacement for any of the above — a different layer. Where it adds value:

- **Proactive reasoning**: asks follow-up questions you didn't know to ask, connects deductions across categories
- **Year-round**: receipt logging, December Sprint, law change alerts, not just filing season
- **Beyond taxes**: salary negotiation, company car math, GKV comparison, investment fee analysis
- **Life events**: full multi-year impact, not just "did your situation change?"
- **Explains the math**: every number shown with the formula behind it

**Honest limitations of TaxDE Skill**: no direct ELSTER submission (guides you, you submit yourself), no customer support team. For complex cases it refers you to a Steuerberater rather than handling them itself.

**The practical split most people end up with**: TaxDE Skill to find everything, understand what's claimable and why, prepare the numbers — then ELSTER or WISO to submit.

---

## Install

```bash
claude skill install taxde.skill
```

Then just start talking:

```
steuern                    → starts a new session
homeoffice absetzen        → jumps straight to Homeoffice calculation
ich habe ein baby bekommen → Life Transition mode
what can I deduct?         → Deduction Hunter
```

---

## What's inside

```
taxde/
├── SKILL.md                          # Main skill (17 sections)
├── scripts/
│   ├── profile_manager.py            # Persistent tax profile (memory)
│   ├── refund_calculator.py          # §32a EStG formula, confidence scoring
│   ├── receipt_logger.py             # Year-round expense tracking
│   └── document_sorter.py           # OCR + auto-classification of tax docs
├── references/
│   ├── deduction-rules.md            # 2024/2025 rules, Pauschalen, limits
│   ├── life-events.md                # 12 major life events, full tax impact
│   ├── scenarios.md                  # 10 simulator templates
│   ├── elster-guide.md               # Field-by-field ELSTER walkthrough
│   ├── expat-guide.md                # DBA treaties, international situations
│   ├── freelancer-guide.md           # EÜR, Gewerbesteuer, Umsatzsteuer
│   ├── financial-blind-spots.md      # Beyond-tax money leaks
│   └── law-change-monitoring.md      # How to track and communicate changes
└── assets/
    ├── folder_structure_template.md  # Suggested document folder structure
    └── steuerberater_handoff.md      # Professional hand-off template
```

---

## Key features

**Leads with your number, not abstract rules.**
"210 Tage × €6 = €1.260 für dich" — not "up to €1,260."

**Proactive by default.**
Every answer triggers an Opportunity Scan. If you mention Homeoffice, TaxDE Skill also checks your commute, your equipment, your union membership.

**Confidence signals on every claim.**
✅ Definitive (§ cited) / ⚠️ Likely / 🔶 Debatable / ❌ Avoid

**December Sprint mode.**
Every November, TaxDE Skill surfaces every year-end move still available — with exact euro amounts and deadlines.

**Steuerberater hand-off, not dismissal.**
Complex cases (US citizenship, RSUs, 3+ countries) get a full briefing package — specific questions to ask, documents to bring, estimated fee range. Never just "see a professional."

**Privacy first.**
Stores only a structured JSON summary in Claude memory. No raw documents, no IBANs, no passwords. Delete everything with "delete my TaxDE Skill profile."

---

## Example session

```
User:         ich bekomme ein Baby
TaxDE Skill:  Herzlichen Glückwunsch! Das ändert einiges — hier ist der vollständige
              Überblick für dieses und die nächsten drei Jahre...

              Sofort (Geburtsjahr):
              • Kindergeld: €250/Monat ab Geburtsmonat → stell den Antrag in den
                ersten 6 Monaten (Ausschlussfrist!)
              • Kinderfreibetrag: €6.612 — ich prüfe automatisch, was für dich
                besser ist (Günstigerprüfung)
              • Kita ab nächstem Jahr: 2/3 der Kosten absetzbar, max. €4.000/Kind

              Was die meisten verpassen:
              • Steuerklassenwechsel zu III/V wenn ein Elternteil Elterngeld bezieht
                kann €X/Monat mehr Netto bedeuten — soll ich das durchrechnen?

[Artifact updates: refund estimate +€640, Kinderfreibetrag added to deductions]
```

---

## Scope and limits

TaxDE Skill handles the vast majority of German tax situations: employees, freelancers, expats, retirees, landlords, investors.

It refers to a Steuerberater (with full briefing) for: US citizenship + German residency, equity compensation from foreign employers, 3+ countries in one year, GmbH structuring >€100k profit, exit taxation (§6 AStG).

Not a substitute for legally binding Steuerberatung (§ 2 StBerG). TaxDE Skill will tell you this once, clearly, and then get to work.

---

*Built for Claude Code. Tested against 2024/2025 German tax law.*
