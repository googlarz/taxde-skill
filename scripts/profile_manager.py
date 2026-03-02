"""
TaxDE Profile Manager
Reads and writes the taxde_profile from Claude's memory system.
All tax profile data is stored as structured JSON — never raw documents.
"""

import json
import os
from datetime import datetime
from typing import Optional

# Memory file path — Claude Code persists this across sessions
MEMORY_DIR = os.path.expanduser("~/.claude/projects")
PROFILE_KEY = "taxde_profile"

# ── Schema ────────────────────────────────────────────────────────────────────

PROFILE_SCHEMA = {
    "meta": {
        "version": "1.0",
        "created": None,          # ISO date string
        "last_updated": None,     # ISO date string
        "tax_year": 2024,
        "language": "de"          # "de" | "en"
    },
    "personal": {
        "name": None,
        "city": None,
        "bundesland": None,
        "kirchensteuer": None,    # bool
        "kirchensteuer_denomination": None  # "ev" | "rk" | None
    },
    "employment": {
        "type": None,             # "angestellter"|"freelancer"|"freiberufler"|"gewerbe"|"mixed"|"rentner"
        "employer_count": None,   # int
        "steuerklasse": None,     # "I"|"II"|"III"|"IV"|"V"|"VI"
        "annual_gross": None,     # float
        "nebenjob": None,         # bool
        "nebenjob_type": None,    # "minijob"|"selbständig"|None
        "nebenjob_income": None   # float
    },
    "family": {
        "status": None,           # "single"|"married"|"divorced"|"civil_partnership"|"widowed"
        "partner_employed": None, # bool
        "partner_steuerklasse": None,
        "partner_annual_gross": None,
        "children": []            # list of child dicts
    },
    "housing": {
        "type": None,             # "mieter"|"eigentuemer"
        "homeoffice_days_per_week": None,
        "homeoffice_room_type": None,  # "dedicated"|"shared"|"none"
        "homeoffice_room_sqm": None,
        "apartment_sqm": None,
        "commute_km": None,
        "commute_days_per_year": None,
        "commute_transport": None,  # "car"|"public"|"both"
        "rental_property": None,
        "rental_property_count": None
    },
    "insurance": {
        "krankenkasse_type": None,      # "gesetzlich"|"privat"
        "krankenkasse_provider": None,
        "zusatzbeitrag_rate": None,     # float, e.g. 0.017 for 1.7%
        "riester": None,                # bool
        "riester_contribution": None,
        "ruerup": None,                 # bool
        "ruerup_contribution": None,
        "bav": None,                    # bool
        "bav_contribution": None
    },
    "special": {
        "expat": None,
        "home_country": None,
        "dba_relevant": None,
        "disability": None,
        "disability_grade": None,
        "gewerkschaft": None,
        "gewerkschaft_beitrag": None,
        "capital_income": None,
        "freistellungsauftrag_set": None
    },
    "filing_history": [],          # list of filing year dicts
    "current_year_receipts": [],   # list of receipt dicts
    "law_changes_noted": []        # list of law change dicts
}

CHILD_SCHEMA = {
    "birth_year": None,
    "kita": None,
    "kita_annual_cost": None,
    "ausbildung": None,
    "ausbildung_away": None
}

FILING_SCHEMA = {
    "year": None,
    "refund": None,
    "filed_date": None,
    "filed_via": None,               # "ELSTER"|"Steuerberater"|"Taxfix"|"TaxDE"
    "steuerbescheid_reviewed": False,
    "einspruch_filed": False,
    "notes": ""
}

RECEIPT_SCHEMA = {
    "date": None,
    "category": None,
    "description": None,
    "amount": None,
    "business_use_pct": 100.0,
    "document_ref": None
}

# ── Storage helpers ────────────────────────────────────────────────────────────

def _get_profile_path() -> str:
    """Return the path where the profile JSON is stored."""
    # Try to find the Claude projects memory dir; fall back to a local .taxde dir
    candidates = [
        os.path.expanduser("~/.claude/projects/taxde_profile.json"),
        os.path.join(os.path.dirname(__file__), "..", ".taxde_profile.json"),
    ]
    # Return first path whose parent dir exists, else default
    for path in candidates:
        if os.path.isdir(os.path.dirname(path)):
            return path
    os.makedirs(os.path.dirname(candidates[0]), exist_ok=True)
    return candidates[0]


def _load_raw() -> dict:
    path = _get_profile_path()
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_raw(data: dict) -> None:
    path = _get_profile_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Public API ────────────────────────────────────────────────────────────────

def get_profile() -> dict:
    """Retrieve current profile. Returns empty dict if none exists."""
    return _load_raw()


def update_profile(updates: dict) -> dict:
    """
    Deep-merge updates into existing profile.
    Lists (children, receipts, etc.) are replaced, not appended, unless the
    caller uses the dedicated add_* helpers below.
    Returns the updated profile.
    """
    profile = _load_raw()

    def deep_merge(base: dict, overlay: dict) -> dict:
        result = dict(base)
        for k, v in overlay.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = deep_merge(result[k], v)
            else:
                result[k] = v
        return result

    if not profile:
        # First write — initialise with schema defaults
        profile = json.loads(json.dumps(PROFILE_SCHEMA))  # deep copy
        profile["meta"]["created"] = datetime.now().isoformat()

    profile["meta"]["last_updated"] = datetime.now().isoformat()
    merged = deep_merge(profile, updates)
    _save_raw(merged)
    return merged


def add_child(child_data: dict) -> dict:
    """Append a child record. Returns updated profile."""
    profile = get_profile() or {}
    children = profile.get("family", {}).get("children", [])
    new_child = dict(CHILD_SCHEMA)
    new_child.update(child_data)
    children.append(new_child)
    return update_profile({"family": {"children": children}})


def add_filing_year(filing_data: dict) -> dict:
    """Append a filing history record. Returns updated profile."""
    profile = get_profile() or {}
    history = profile.get("filing_history", [])
    # Replace existing year if present
    year = filing_data.get("year")
    history = [h for h in history if h.get("year") != year]
    new_entry = dict(FILING_SCHEMA)
    new_entry.update(filing_data)
    history.append(new_entry)
    history.sort(key=lambda x: x.get("year", 0))
    return update_profile({"filing_history": history})


def delete_profile() -> bool:
    """Delete all profile data. Returns True if successful."""
    path = _get_profile_path()
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def display_profile() -> str:
    """Return a human-readable summary of stored profile."""
    p = get_profile()
    if not p:
        return "No TaxDE profile found. Start a conversation to create one."

    lines = ["═══ Your TaxDE Profile ═══\n"]

    meta = p.get("meta", {})
    lines.append(f"Tax year: {meta.get('tax_year', '—')}  |  "
                 f"Last updated: {meta.get('last_updated', '—')[:10] if meta.get('last_updated') else '—'}")

    personal = p.get("personal", {})
    if personal.get("name"):
        lines.append(f"\nName: {personal['name']}")
    if personal.get("city"):
        lines.append(f"Location: {personal['city']}, {personal.get('bundesland', '')}")
    if personal.get("kirchensteuer") is not None:
        kt = "Yes" if personal["kirchensteuer"] else "No"
        lines.append(f"Kirchensteuer: {kt}")

    emp = p.get("employment", {})
    if emp.get("type"):
        lines.append(f"\nEmployment: {emp['type']}")
    if emp.get("steuerklasse"):
        lines.append(f"Steuerklasse: {emp['steuerklasse']}")
    if emp.get("annual_gross"):
        lines.append(f"Annual gross: €{emp['annual_gross']:,.0f}")
    if emp.get("nebenjob"):
        lines.append(f"Nebenjob: {emp.get('nebenjob_type', 'yes')} — €{emp.get('nebenjob_income', 0):,.0f}")

    fam = p.get("family", {})
    if fam.get("status"):
        lines.append(f"\nFamily status: {fam['status']}")
    children = fam.get("children", [])
    if children:
        lines.append(f"Children: {len(children)}")
        for i, c in enumerate(children, 1):
            kita = " (Kita)" if c.get("kita") else ""
            lines.append(f"  Child {i}: born {c.get('birth_year', '?')}{kita}")

    housing = p.get("housing", {})
    if housing.get("homeoffice_days_per_week"):
        lines.append(f"\nHomeoffice: {housing['homeoffice_days_per_week']} days/week")
    if housing.get("commute_km"):
        lines.append(f"Commute: {housing['commute_km']} km, "
                     f"{housing.get('commute_days_per_year', '?')} days/year")

    ins = p.get("insurance", {})
    if ins.get("krankenkasse_type"):
        provider = ins.get("krankenkasse_provider", "")
        lines.append(f"\nKrankenkasse: {ins['krankenkasse_type']} {provider}")
    pensions = []
    if ins.get("riester"):
        pensions.append(f"Riester €{ins.get('riester_contribution', 0):,.0f}")
    if ins.get("ruerup"):
        pensions.append(f"Rürup €{ins.get('ruerup_contribution', 0):,.0f}")
    if ins.get("bav"):
        pensions.append(f"bAV €{ins.get('bav_contribution', 0):,.0f}")
    if pensions:
        lines.append(f"Pension contributions: {', '.join(pensions)}")

    history = p.get("filing_history", [])
    if history:
        lines.append("\nFiling history:")
        for h in history[-3:]:  # last 3 years
            refund = f"€{h['refund']:,.0f}" if h.get("refund") is not None else "pending"
            lines.append(f"  {h.get('year', '?')}: refund {refund} via {h.get('filed_via', '?')}")

    receipts = p.get("current_year_receipts", [])
    if receipts:
        total = sum(r.get("amount", 0) * r.get("business_use_pct", 100) / 100 for r in receipts)
        lines.append(f"\nRunning receipt log: {len(receipts)} items, ~€{total:,.0f} deductible")

    lines.append("\n[Say 'delete my TaxDE profile' to wipe all stored data]")
    return "\n".join(lines)


def get_missing_fields() -> list:
    """Return list of high-priority profile fields not yet populated."""
    p = get_profile()
    if not p:
        return ["entire profile — not yet created"]

    missing = []
    checks = [
        ("employment.annual_gross", p.get("employment", {}).get("annual_gross")),
        ("employment.steuerklasse", p.get("employment", {}).get("steuerklasse")),
        ("personal.bundesland", p.get("personal", {}).get("bundesland")),
        ("personal.kirchensteuer", p.get("personal", {}).get("kirchensteuer")),
        ("family.status", p.get("family", {}).get("status")),
        ("housing.homeoffice_days_per_week", p.get("housing", {}).get("homeoffice_days_per_week")),
        ("housing.commute_km", p.get("housing", {}).get("commute_km")),
        ("insurance.krankenkasse_type", p.get("insurance", {}).get("krankenkasse_type")),
    ]
    for field, value in checks:
        if value is None:
            missing.append(field)
    return missing


def get_profile_completeness_pct() -> int:
    """Return an integer 0-100 representing profile completeness."""
    all_fields = [
        "employment.annual_gross", "employment.steuerklasse", "employment.type",
        "personal.name", "personal.bundesland", "personal.kirchensteuer",
        "family.status",
        "housing.homeoffice_days_per_week", "housing.commute_km", "housing.type",
        "insurance.krankenkasse_type",
        "special.expat",
    ]
    missing = get_missing_fields()
    filled = len(all_fields) - len([m for m in missing if m in all_fields])
    return int(filled / len(all_fields) * 100)


if __name__ == "__main__":
    # Quick smoke test
    print("Testing profile_manager...")
    delete_profile()
    assert get_profile() == {}

    update_profile({
        "meta": {"tax_year": 2024, "language": "de"},
        "personal": {"name": "Max Mustermann", "city": "Berlin", "bundesland": "Berlin"},
        "employment": {"type": "angestellter", "steuerklasse": "I", "annual_gross": 65000},
    })
    p = get_profile()
    assert p["personal"]["name"] == "Max Mustermann"
    assert p["employment"]["annual_gross"] == 65000

    print(display_profile())
    print("Missing fields:", get_missing_fields())
    print("Completeness:", get_profile_completeness_pct(), "%")
    delete_profile()
    print("All tests passed.")
