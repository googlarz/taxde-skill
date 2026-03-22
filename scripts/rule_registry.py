"""
Rule registry with provenance metadata for critical TaxDE figures.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

try:
    from tax_dates import format_deadline_label, get_filing_deadline
    from tax_rules import TAX_YEAR_RULES, resolve_supported_year
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.dirname(__file__))
    from tax_dates import format_deadline_label, get_filing_deadline
    from tax_rules import TAX_YEAR_RULES, resolve_supported_year


DEFAULT_PROVENANCE = {
    "source_title": "Bundled TaxDE rule",
    "source_url": None,
    "verified_date": None,
    "verification_method": "bundled_manual_review",
}


CRITICAL_RULE_PROVENANCE = {
    2024: {
        "grundfreibetrag": {
            "source_title": "BMF January 2025 tax changes overview",
            "source_url": "https://www.bundesfinanzministerium.de/Monatsberichte/Ausgabe/2025/01/Inhalte/Kapitel-2-Fokus/die-wichtigsten-steuerlichen-aenderungen-2025.html?nn=237786",
            "verified_date": "2026-03-22",
            "verification_method": "official_html_review",
        },
        "kindergeld_per_child": {
            "source_title": "BMF January 2025 tax changes overview",
            "source_url": "https://www.bundesfinanzministerium.de/Monatsberichte/Ausgabe/2025/01/Inhalte/Kapitel-2-Fokus/die-wichtigsten-steuerlichen-aenderungen-2025.html?nn=237786",
            "verified_date": "2026-03-22",
            "verification_method": "official_html_review",
        },
        "kinderfreibetrag_child": {
            "source_title": "BMF January 2025 tax changes overview",
            "source_url": "https://www.bundesfinanzministerium.de/Monatsberichte/Ausgabe/2025/01/Inhalte/Kapitel-2-Fokus/die-wichtigsten-steuerlichen-aenderungen-2025.html?nn=237786",
            "verified_date": "2026-03-22",
            "verification_method": "official_html_review",
        },
    },
    2025: {
        "grundfreibetrag": {
            "source_title": "BMF January 2025 tax changes overview",
            "source_url": "https://www.bundesfinanzministerium.de/Monatsberichte/Ausgabe/2025/01/Inhalte/Kapitel-2-Fokus/die-wichtigsten-steuerlichen-aenderungen-2025.html?nn=237786",
            "verified_date": "2026-03-22",
            "verification_method": "official_html_review",
        },
        "kindergeld_per_child": {
            "source_title": "BMF January 2025 tax changes overview",
            "source_url": "https://www.bundesfinanzministerium.de/Monatsberichte/Ausgabe/2025/01/Inhalte/Kapitel-2-Fokus/die-wichtigsten-steuerlichen-aenderungen-2025.html?nn=237786",
            "verified_date": "2026-03-22",
            "verification_method": "official_html_review",
        },
        "kinderfreibetrag_child": {
            "source_title": "BMF January 2025 tax changes overview",
            "source_url": "https://www.bundesfinanzministerium.de/Monatsberichte/Ausgabe/2025/01/Inhalte/Kapitel-2-Fokus/die-wichtigsten-steuerlichen-aenderungen-2025.html?nn=237786",
            "verified_date": "2026-03-22",
            "verification_method": "official_html_review",
        },
        "kinderbetreuung_pct": {
            "source_title": "BMF January 2025 tax changes overview",
            "source_url": "https://www.bundesfinanzministerium.de/Monatsberichte/Ausgabe/2025/01/Inhalte/Kapitel-2-Fokus/die-wichtigsten-steuerlichen-aenderungen-2025.html?nn=237786",
            "verified_date": "2026-03-22",
            "verification_method": "official_html_review",
        },
        "kinderbetreuung_max": {
            "source_title": "BMF January 2025 tax changes overview",
            "source_url": "https://www.bundesfinanzministerium.de/Monatsberichte/Ausgabe/2025/01/Inhalte/Kapitel-2-Fokus/die-wichtigsten-steuerlichen-aenderungen-2025.html?nn=237786",
            "verified_date": "2026-03-22",
            "verification_method": "official_html_review",
        },
    },
    2026: {
        "grundfreibetrag": {
            "source_title": "BMF 2026 tax changes overview",
            "source_url": "https://www.bundesfinanzministerium.de/Content/DE/Standardartikel/Themen/Steuern/das-aendert-sich-2026.html",
            "verified_date": "2026-03-22",
            "verification_method": "official_html_review",
        },
        "kindergeld_per_child": {
            "source_title": "BMF 2026 tax changes overview",
            "source_url": "https://www.bundesfinanzministerium.de/Content/DE/Standardartikel/Themen/Steuern/das-aendert-sich-2026.html",
            "verified_date": "2026-03-22",
            "verification_method": "official_html_review",
        },
        "kinderfreibetrag_child": {
            "source_title": "BMF 2026 tax changes overview",
            "source_url": "https://www.bundesfinanzministerium.de/Content/DE/Standardartikel/Themen/Steuern/das-aendert-sich-2026.html",
            "verified_date": "2026-03-22",
            "verification_method": "official_html_review",
        },
        "kinderbetreuung_pct": {
            "source_title": "TaxDE bundled 2026 carry-forward from 2025 childcare rule",
            "source_url": "https://www.bundesfinanzministerium.de/Monatsberichte/Ausgabe/2025/01/Inhalte/Kapitel-2-Fokus/die-wichtigsten-steuerlichen-aenderungen-2025.html?nn=237786",
            "verified_date": "2026-03-22",
            "verification_method": "official_html_review",
        },
        "kinderbetreuung_max": {
            "source_title": "TaxDE bundled 2026 carry-forward from 2025 childcare rule",
            "source_url": "https://www.bundesfinanzministerium.de/Monatsberichte/Ausgabe/2025/01/Inhalte/Kapitel-2-Fokus/die-wichtigsten-steuerlichen-aenderungen-2025.html?nn=237786",
            "verified_date": "2026-03-22",
            "verification_method": "official_html_review",
        },
    },
}


DEADLINE_PROVENANCE = {
    2024: {
        "source_title": "BMF AO guidance for transitional filing deadlines",
        "source_url": "https://erbsth.bundesfinanzministerium.de/ao/2024/Anhaenge/BMF-Schreiben-und-gleichlautende-Laendererlasse/Anhang-51/inhalt.html",
        "verified_date": "2026-03-22",
        "verification_method": "official_html_review",
    }
}


def _freshness_state(requested_year: int, resolved_year: int, verified_date: Optional[str]) -> str:
    if requested_year != resolved_year:
        return "fallback"
    if verified_date:
        return "verified"
    return "bundled"


def get_rule_registry(year: int) -> dict:
    resolved_year, note = resolve_supported_year(year)
    rules = TAX_YEAR_RULES[resolved_year]
    registry = {}
    generated_at = datetime.now().isoformat(timespec="seconds")

    for key, value in rules.items():
        provenance = dict(DEFAULT_PROVENANCE)
        provenance.update(CRITICAL_RULE_PROVENANCE.get(resolved_year, {}).get(key, {}))
        registry[key] = {
            "value": value,
            "year": resolved_year,
            "requested_year": year,
            "source_title": provenance["source_title"],
            "source_url": provenance["source_url"],
            "verified_date": provenance["verified_date"],
            "verification_method": provenance["verification_method"],
            "freshness_state": _freshness_state(year, resolved_year, provenance["verified_date"]),
        }

    standard_deadline = get_filing_deadline(resolved_year, advised=False)
    advised_deadline = get_filing_deadline(resolved_year, advised=True)
    deadline_provenance = dict(DEFAULT_PROVENANCE)
    deadline_provenance.update(DEADLINE_PROVENANCE.get(resolved_year, {}))

    return {
        "generated_at": generated_at,
        "requested_year": year,
        "resolved_year": resolved_year,
        "fallback_note": note,
        "rules": registry,
        "deadlines": {
            "standard": {
                "value": standard_deadline.isoformat(),
                "label": format_deadline_label(resolved_year, advised=False),
                **deadline_provenance,
            },
            "advised": {
                "value": advised_deadline.isoformat(),
                "label": format_deadline_label(resolved_year, advised=True),
                **deadline_provenance,
            },
        },
    }


def format_rule_registry_display(registry: dict) -> str:
    lines = [
        f"TaxDE rule registry for {registry['requested_year']} "
        f"(using {registry['resolved_year']})",
    ]
    if registry.get("fallback_note"):
        lines.append(f"⚠️  {registry['fallback_note']}")
    lines.append("")

    for key in (
        "grundfreibetrag",
        "kindergeld_per_child",
        "kinderfreibetrag_child",
        "kinderbetreuung_pct",
        "kinderbetreuung_max",
    ):
        entry = registry["rules"].get(key)
        if not entry:
            continue
        lines.append(
            f"- {key}: {entry['value']} "
            f"[{entry['freshness_state']}]"
        )
        if entry.get("source_title"):
            lines.append(f"  Source: {entry['source_title']}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_rule_registry_display(get_rule_registry(2026)))
