"""
Tax filing deadline helpers.

The transitional advised deadlines for tax years 2023 and 2024 come from the
official BMF guidance on the extended filing periods. For later years, the
regular AO deadlines apply again.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date


ADVISED_DEADLINES = {
    False: {
        2023: date(2025, 6, 2),
        2024: date(2026, 4, 30),
    },
    True: {
        2023: date(2025, 11, 3),
        2024: date(2026, 9, 30),
    },
}


def _last_day_of_february(year: int) -> int:
    return monthrange(year, 2)[1]


def get_filing_deadline(
    tax_year: int,
    advised: bool = False,
    agriculture: bool = False,
) -> date:
    transition = ADVISED_DEADLINES[agriculture]
    if advised and tax_year in transition:
        return transition[tax_year]

    if advised and agriculture:
        return date(tax_year + 2, 7, 31)

    if advised:
        return date(tax_year + 2, 2, _last_day_of_february(tax_year + 2))

    return date(tax_year + 1, 7, 31)


def format_deadline_label(
    tax_year: int,
    advised: bool = False,
    agriculture: bool = False,
) -> str:
    deadline = get_filing_deadline(tax_year, advised=advised, agriculture=agriculture)
    label = "with tax adviser" if advised else "without tax adviser"
    if agriculture:
        label += ", agriculture case"
    return f"{deadline.isoformat()} ({label})"
