"""
Safe TaxDE rule update pipeline.

This script monitors a small set of official sources, extracts tracked figures,
compares them to the bundled rules, and drafts a reviewable update proposal.
It does not modify the repository unless the user explicitly applies a saved
proposal directory.
"""

from __future__ import annotations

import argparse
import difflib
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional

try:
    from tax_dates import ADVISED_DEADLINES
    from tax_rules import TAX_YEAR_RULES
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from tax_dates import ADVISED_DEADLINES
    from tax_rules import TAX_YEAR_RULES


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROPOSAL_ROOT = REPO_ROOT / ".taxde-updates"
HTTP_USER_AGENT = "TaxDE-Rule-Updater/1.0"
TRACKED_FILES = (
    "scripts/tax_rules.py",
    "scripts/tax_dates.py",
    "references/deduction-rules.md",
    "tests/test_tax_rules.py",
    "tests/test_tax_dates.py",
    "tests/test_refund_calculator.py",
)


@dataclass(frozen=True)
class ExtractionSpec:
    key: str
    pattern: str
    value_type: str = "int"
    flags: int = re.IGNORECASE
    group: int = 1


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    label: str
    url: str
    extractors: tuple[ExtractionSpec, ...]


@dataclass(frozen=True)
class DetectedChange:
    key: str
    current_value: object
    proposed_value: object
    source_id: str
    source_label: str
    source_url: str
    derived_from: str
    change_type: str
    severity: str


SOURCE_SPECS = (
    SourceSpec(
        source_id="bmf_changes_2025",
        label="BMF January 2025 tax changes overview",
        url=(
            "https://www.bundesfinanzministerium.de/Monatsberichte/Ausgabe/2025/01/"
            "Inhalte/Kapitel-2-Fokus/die-wichtigsten-steuerlichen-aenderungen-2025.html?nn=237786"
        ),
        extractors=(
            ExtractionSpec(
                key="tax_rules.2025.grundfreibetrag",
                pattern=(
                    r"Mit der Anhebung des in den Einkommensteuertarif integrierten "
                    r"Grundfreibetrags um [0-9.]+ Euro auf ([0-9.]+) Euro"
                ),
            ),
            ExtractionSpec(
                key="tax_rules.2025.kindergeld_per_child",
                pattern=r"zum 1\.\s*Januar 2025 um [0-9.]+ Euro auf ([0-9.]+) Euro",
            ),
            ExtractionSpec(
                key="tax_rules.2025.kinderfreibetrag_total",
                pattern=(
                    r"auf insgesamt [0-9.]+ Euro pro Elternteil beziehungsweise "
                    r"([0-9.]+) Euro pro Kind"
                ),
            ),
            ExtractionSpec(
                key="tax_rules.2025.kinderbetreuung_pct_percent",
                pattern=r"Begrenzung auf ([0-9]+) Prozent der Aufwendungen",
            ),
            ExtractionSpec(
                key="tax_rules.2025.kinderbetreuung_max",
                pattern=r"Kinderbetreuungskosten auf ([0-9.]+) Euro je Kind erhöht",
            ),
        ),
    ),
    SourceSpec(
        source_id="bmf_changes_2026",
        label="BMF 2026 tax changes overview",
        url=(
            "https://www.bundesfinanzministerium.de/Content/DE/Standardartikel/"
            "Themen/Steuern/das-aendert-sich-2026.html"
        ),
        extractors=(
            ExtractionSpec(
                key="tax_rules.2026.grundfreibetrag",
                pattern=r"2026 steigt er um [0-9.]+ Euro auf ([0-9.]+) Euro",
            ),
            ExtractionSpec(
                key="tax_rules.2026.kindergeld_per_child",
                pattern=r"Kindergeld steigt um [0-9.]+ Euro auf ([0-9.]+) Euro pro Kind",
            ),
            ExtractionSpec(
                key="tax_rules.2026.kinderfreibetrag_total",
                pattern=r"Kinderfreibetrag steigt 2026 um [0-9.]+ Euro auf ([0-9.]+) Euro",
            ),
        ),
    ),
    SourceSpec(
        source_id="bmf_deadlines_2024",
        label="BMF AO filing deadline guidance for transitional years",
        url=(
            "https://erbsth.bundesfinanzministerium.de/ao/2024/Anhaenge/"
            "BMF-Schreiben-und-gleichlautende-Laendererlasse/Anhang-51/inhalt.html"
        ),
        extractors=(
            ExtractionSpec(
                key="tax_dates.standard.2024",
                pattern=r"für den Besteuerungszeitraum 2024\s*:\s*der\s*([0-9]{1,2}\.\s*[A-Za-zäöüÄÖÜ]+\s*[0-9]{4})",
                value_type="date_de",
            ),
            ExtractionSpec(
                key="tax_dates.agriculture.2024",
                pattern=r"für den Besteuerungszeitraum 2024\s*:\s*der\s*(30\.\s*September\s*2026)",
                value_type="date_de",
            ),
        ),
    ),
)


REFERENCE_ROW_MAP = {
    "grundfreibetrag": "Grundfreibetrag",
    "kindergeld_per_child": "Kindergeld per child",
    "kinderfreibetrag_child": "Kinderfreibetrag (Sachbedarf/Elternteil)",
    "kinderbetreuung_pct": "Kinderbetreuung deductible share",
    "kinderbetreuung_max": "Kinderbetreuung max per child",
}


MONTHS_DE = {
    "januar": 1,
    "februar": 2,
    "märz": 3,
    "maerz": 3,
    "april": 4,
    "mai": 5,
    "juni": 6,
    "juli": 7,
    "august": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "dezember": 12,
}


def clean_source_text(raw_text: str) -> str:
    text = html.unescape(raw_text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def parse_german_date(value: str) -> date:
    match = re.match(r"([0-9]{1,2})\.\s*([A-Za-zäöüÄÖÜ]+)\s*([0-9]{4})", value.strip())
    if not match:
        raise ValueError(f"Could not parse German date: {value!r}")
    day = int(match.group(1))
    month_name = match.group(2).lower()
    month = MONTHS_DE.get(month_name)
    if month is None:
        raise ValueError(f"Unknown German month: {month_name!r}")
    year = int(match.group(3))
    return date(year, month, day)


def parse_extracted_value(value: str, value_type: str) -> object:
    raw = value.strip()
    if value_type == "int":
        return int(raw.replace(".", ""))
    if value_type == "date_de":
        return parse_german_date(raw)
    raise ValueError(f"Unsupported value_type: {value_type}")


def fetch_url_text(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": HTTP_USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "ignore")


def collect_snapshot(
    fetcher: Callable[[str], str] = fetch_url_text,
) -> tuple[dict, dict]:
    snapshot: dict[str, dict] = {}
    source_lookup: dict[str, dict] = {}

    for spec in SOURCE_SPECS:
        raw_text = fetcher(spec.url)
        cleaned = clean_source_text(raw_text)
        extracted: dict[str, dict] = {}
        for extractor in spec.extractors:
            match = re.search(extractor.pattern, cleaned, extractor.flags)
            if not match:
                continue
            raw_value = match.group(extractor.group)
            parsed_value = parse_extracted_value(raw_value, extractor.value_type)
            extracted[extractor.key] = {
                "raw": raw_value,
                "value": (
                    parsed_value.isoformat() if isinstance(parsed_value, date) else parsed_value
                ),
                "pattern": extractor.pattern,
                "value_type": extractor.value_type,
            }
            source_lookup[extractor.key] = {
                "source_id": spec.source_id,
                "source_label": spec.label,
                "source_url": spec.url,
                "derived_from": extractor.key,
            }
        snapshot[spec.source_id] = {
            "label": spec.label,
            "url": spec.url,
            "extracted": extracted,
        }
    return snapshot, source_lookup


def flatten_snapshot_values(snapshot: dict) -> dict[str, object]:
    values: dict[str, object] = {}
    for source in snapshot.values():
        for key, payload in source["extracted"].items():
            value = payload["value"]
            if payload["value_type"] == "date_de":
                value = date.fromisoformat(value)
            values[key] = value
    return values


def build_normalized_snapshot_entries(snapshot: dict) -> list[dict]:
    entries = []
    for source_id, source in snapshot.items():
        for key, payload in source["extracted"].items():
            parts = key.split(".")
            if parts[0] == "tax_rules":
                year = int(parts[1])
                field = parts[2]
                family = "tax_rules"
            else:
                year = int(parts[2])
                field = parts[1]
                family = "tax_dates"
            entries.append(
                {
                    "key": key,
                    "family": family,
                    "year": year,
                    "field": field,
                    "value": payload["value"],
                    "value_type": payload["value_type"],
                    "source_id": source_id,
                    "source_title": source["label"],
                    "source_url": source["url"],
                }
            )
    return sorted(entries, key=lambda item: item["key"])


def derive_proposed_updates(
    snapshot_values: dict[str, object],
    source_lookup: dict[str, dict],
) -> tuple[dict, dict[str, dict]]:
    proposed = {"tax_rules": {}, "tax_dates": {False: {}, True: {}}}
    derived_lookup: dict[str, dict] = {}

    for key, value in snapshot_values.items():
        parts = key.split(".")
        if parts[0] == "tax_rules":
            year = int(parts[1])
            field = parts[2]
            proposed["tax_rules"].setdefault(year, {})
            if field == "kinderfreibetrag_total":
                bea = TAX_YEAR_RULES[year]["kinderfreibetrag_bea"]
                child_component = int((int(value) - 2 * int(bea)) / 2)
                target_key = f"tax_rules.{year}.kinderfreibetrag_child"
                proposed["tax_rules"][year]["kinderfreibetrag_child"] = child_component
                derived_lookup[target_key] = {
                    **source_lookup[key],
                    "derived_from": key,
                }
            elif field == "kinderbetreuung_pct_percent":
                target_key = f"tax_rules.{year}.kinderbetreuung_pct"
                proposed["tax_rules"][year]["kinderbetreuung_pct"] = round(int(value) / 100, 2)
                derived_lookup[target_key] = {
                    **source_lookup[key],
                    "derived_from": key,
                }
            else:
                target_key = f"tax_rules.{year}.{field}"
                proposed["tax_rules"][year][field] = value
                derived_lookup[target_key] = {
                    **source_lookup[key],
                    "derived_from": key,
                }
        elif parts[0] == "tax_dates":
            bucket = parts[1] == "agriculture"
            year = int(parts[2])
            proposed["tax_dates"][bucket][year] = value
            derived_lookup[key] = {
                **source_lookup[key],
                "derived_from": key,
            }
    return proposed, derived_lookup


def detect_changes(proposed: dict, derived_lookup: dict[str, dict]) -> list[DetectedChange]:
    changes: list[DetectedChange] = []

    for year, fields in proposed["tax_rules"].items():
        current_rules = TAX_YEAR_RULES.get(year, {})
        for field, proposed_value in fields.items():
            current_value = current_rules.get(field)
            if current_value != proposed_value:
                key = f"tax_rules.{year}.{field}"
                source = derived_lookup[key]
                change_type, severity = classify_change_key(key)
                changes.append(
                    DetectedChange(
                        key=key,
                        current_value=current_value,
                        proposed_value=proposed_value,
                        source_id=source["source_id"],
                        source_label=source["source_label"],
                        source_url=source["source_url"],
                        derived_from=source["derived_from"],
                        change_type=change_type,
                        severity=severity,
                    )
                )

    for agriculture, year_map in proposed["tax_dates"].items():
        current_dates = ADVISED_DEADLINES[agriculture]
        for year, proposed_value in year_map.items():
            current_value = current_dates.get(year)
            if current_value != proposed_value:
                key = f"tax_dates.{ 'agriculture' if agriculture else 'standard' }.{year}"
                source = derived_lookup[key]
                change_type, severity = classify_change_key(key)
                changes.append(
                    DetectedChange(
                        key=key,
                        current_value=current_value,
                        proposed_value=proposed_value,
                        source_id=source["source_id"],
                        source_label=source["source_label"],
                        source_url=source["source_url"],
                        derived_from=source["derived_from"],
                        change_type=change_type,
                        severity=severity,
                    )
                )

    return sorted(changes, key=lambda item: item.key)


def classify_change_key(key: str) -> tuple[str, str]:
    if key.startswith("tax_dates."):
        return "deadline", "high"
    if any(token in key for token in ("grundfreibetrag", "zone", "spitzen", "reichen", "soli")):
        return "tariff_parameter", "high"
    if any(token in key for token in ("kindergeld", "kinderfreibetrag", "kinderbetreuung")):
        return "family_threshold", "medium"
    if any(token in key for token in ("riester", "ruerup", "bav")):
        return "contribution_limit", "medium"
    return "threshold", "low"


def format_python_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, int):
        return f"{value:_}"
    if isinstance(value, float):
        return f"{value:.2f}"
    if value is None:
        return "None"
    raise TypeError(f"Unsupported Python scalar: {value!r}")


def format_date_ctor(value: date) -> str:
    return f"date({value.year}, {value.month}, {value.day})"


def patch_tax_rules_text(text: str, updates_by_year: dict[int, dict[str, object]]) -> str:
    lines = text.splitlines()
    current_year: Optional[int] = None
    depth = 0

    for index, line in enumerate(lines):
        if current_year is None:
            year_match = re.match(r"\s*(\d{4}):\s*\{", line)
            if year_match:
                current_year = int(year_match.group(1))
                depth = line.count("{") - line.count("}")
            continue

        if current_year in updates_by_year and depth == 1:
            field_match = re.match(r'(\s*"([^"]+)":\s*)([^,]+)(,?)', line)
            if field_match:
                field_name = field_match.group(2)
                if field_name in updates_by_year[current_year]:
                    replacement = format_python_scalar(updates_by_year[current_year][field_name])
                    lines[index] = (
                        f"{field_match.group(1)}{replacement}{field_match.group(4)}"
                    )

        depth += line.count("{") - line.count("}")
        if depth == 0:
            current_year = None

    return "\n".join(lines) + "\n"


def patch_tax_dates_text(text: str, updates_by_bucket: dict[bool, dict[int, date]]) -> str:
    lines = text.splitlines()
    current_bucket: Optional[bool] = None
    depth = 0

    for index, line in enumerate(lines):
        if current_bucket is None:
            bucket_match = re.match(r"\s*(False|True):\s*\{", line)
            if bucket_match:
                current_bucket = bucket_match.group(1) == "True"
                depth = line.count("{") - line.count("}")
            continue

        if depth == 1 and current_bucket in updates_by_bucket:
            year_match = re.match(r"(\s*)(\d{4}):\s*date\([^)]+\)(,?)", line)
            if year_match:
                year = int(year_match.group(2))
                replacement_date = updates_by_bucket[current_bucket].get(year)
                if replacement_date:
                    lines[index] = (
                        f"{year_match.group(1)}{year}: "
                        f"{format_date_ctor(replacement_date)}{year_match.group(3)}"
                    )

        depth += line.count("{") - line.count("}")
        if depth == 0:
            current_bucket = None

    return "\n".join(lines) + "\n"


def format_reference_cell(row_label: str, value: object) -> str:
    if row_label == "Kindergeld per child":
        return f"€{int(value):,}/mo"
    if row_label == "Kinderbetreuung deductible share":
        if abs(float(value) - (2 / 3)) < 1e-9:
            return "2/3"
        return f"{int(round(float(value) * 100))}%"
    if isinstance(value, int):
        return f"€{value:,}"
    raise TypeError(f"Unsupported reference row value for {row_label!r}: {value!r}")


def patch_deduction_rules_text(text: str, updates_by_year: dict[int, dict[str, object]]) -> str:
    lines = text.splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.startswith("| Item |"))
    header_cells = [cell.strip() for cell in lines[header_index].split("|")[1:-1]]
    year_to_column = {int(name): idx for idx, name in enumerate(header_cells) if name.isdigit()}

    for index, line in enumerate(lines):
        if not line.startswith("| ") or line.startswith("|------"):
            continue
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if not cells:
            continue
        row_label = cells[0]
        for year, fields in updates_by_year.items():
            if year not in year_to_column:
                continue
            column_index = year_to_column[year]
            for field, value in fields.items():
                if REFERENCE_ROW_MAP.get(field) == row_label:
                    cells[column_index] = format_reference_cell(row_label, value)
        lines[index] = "| " + " | ".join(cells) + " |"

    return "\n".join(lines) + "\n"


def replace_regex(text: str, pattern: str, replacement: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"Expected one replacement for pattern: {pattern}")
    return updated


def patch_test_tax_rules_text(text: str, updates_by_year: dict[int, dict[str, object]]) -> str:
    for year, fields in updates_by_year.items():
        if "grundfreibetrag" in fields:
            expected = format_python_scalar(int(fields["grundfreibetrag"]))
            text = replace_regex(
                text,
                rf"(self\.assertEqual\(calculate_income_tax\()[\d_]+(,\s*{year}\),\s*0\.0\))",
                rf"\g<1>{expected}\g<2>",
            )
        if year == 2026:
            if "grundfreibetrag" in fields:
                text = replace_regex(
                    text,
                    r'(self\.assertEqual\(rules\["grundfreibetrag"\],\s*)[\d_]+(\))',
                    rf"\g<1>{format_python_scalar(int(fields['grundfreibetrag']))}\g<2>",
                )
            if "kindergeld_per_child" in fields:
                text = replace_regex(
                    text,
                    r'(self\.assertEqual\(rules\["kindergeld_per_child"\],\s*)[\d_]+(\))',
                    rf"\g<1>{format_python_scalar(int(fields['kindergeld_per_child']))}\g<2>",
                )
            if "kinderfreibetrag_child" in fields:
                text = replace_regex(
                    text,
                    r'(self\.assertEqual\(rules\["kinderfreibetrag_child"\],\s*)[\d_]+(\))',
                    rf"\g<1>{format_python_scalar(int(fields['kinderfreibetrag_child']))}\g<2>",
                )
            if "kinderbetreuung_pct" in fields:
                text = replace_regex(
                    text,
                    r'(self\.assertAlmostEqual\(rules\["kinderbetreuung_pct"\],\s*)[0-9.]+(\))',
                    rf"\g<1>{fields['kinderbetreuung_pct']:.2f}\g<2>",
                )
            if "kinderbetreuung_max" in fields:
                text = replace_regex(
                    text,
                    r'(self\.assertEqual\(rules\["kinderbetreuung_max"\],\s*)[\d_]+(\))',
                    rf"\g<1>{format_python_scalar(int(fields['kinderbetreuung_max']))}\g<2>",
                )
    return text


def patch_test_tax_dates_text(text: str, updates_by_bucket: dict[bool, dict[int, date]]) -> str:
    standard_deadline = updates_by_bucket.get(False, {}).get(2024)
    if standard_deadline:
        replacement = format_date_ctor(standard_deadline)
        text = replace_regex(
            text,
            r"(self\.assertEqual\(get_filing_deadline\(2024, advised=True\),\s*)date\([^)]+\)(\))",
            rf"\g<1>{replacement}\g<2>",
        )
    return text


def patch_test_refund_calculator_text(
    text: str,
    updates_by_year: dict[int, dict[str, object]],
) -> str:
    year_2025 = dict(TAX_YEAR_RULES[2025])
    year_2025.update(updates_by_year.get(2025, {}))
    expected_total = 36 + min(10_000 * year_2025["kinderbetreuung_pct"], year_2025["kinderbetreuung_max"])
    expected_literal = f"{expected_total:.1f}"
    return replace_regex(
        text,
        r'(self\.assertEqual\(result\["breakdown"\]\["total_sonderausgaben"\],\s*)[0-9.]+(\))',
        rf"\g<1>{expected_literal}\g<2>",
    )


def apply_updates_to_repo(repo_root: Path, proposed: dict) -> list[str]:
    changed_files: list[str] = []

    file_updaters = {
        "scripts/tax_rules.py": lambda text: patch_tax_rules_text(text, proposed["tax_rules"]),
        "scripts/tax_dates.py": lambda text: patch_tax_dates_text(text, proposed["tax_dates"]),
        "references/deduction-rules.md": lambda text: patch_deduction_rules_text(text, proposed["tax_rules"]),
        "tests/test_tax_rules.py": lambda text: patch_test_tax_rules_text(text, proposed["tax_rules"]),
        "tests/test_tax_dates.py": lambda text: patch_test_tax_dates_text(text, proposed["tax_dates"]),
        "tests/test_refund_calculator.py": lambda text: patch_test_refund_calculator_text(text, proposed["tax_rules"]),
    }

    for relative_path, updater in file_updaters.items():
        path = repo_root / relative_path
        original = path.read_text(encoding="utf-8")
        updated = updater(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed_files.append(relative_path)

    return changed_files


def copy_repo_to_temp(repo_root: Path, temp_root: Path) -> Path:
    worktree = temp_root / "repo"
    shutil.copytree(
        repo_root,
        worktree,
        ignore=shutil.ignore_patterns(".git", "__pycache__", ".taxde", ".taxde-updates"),
    )
    return worktree


def run_verification(repo_root: Path) -> list[dict]:
    commands = [
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        [sys.executable, "-m", "compileall", "scripts", "tests"],
    ]
    results = []
    for command in commands:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        results.append(
            {
                "command": " ".join(command),
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )
    return results


def create_unified_diff(repo_root: Path, updated_root: Path, changed_files: list[str]) -> str:
    chunks = []
    for relative_path in changed_files:
        original = (repo_root / relative_path).read_text(encoding="utf-8").splitlines(keepends=True)
        updated = (updated_root / relative_path).read_text(encoding="utf-8").splitlines(keepends=True)
        diff = difflib.unified_diff(
            original,
            updated,
            fromfile=relative_path,
            tofile=relative_path,
        )
        chunks.extend(diff)
    return "".join(chunks)


def write_proposal_bundle(
    proposal_root: Path,
    repo_root: Path,
    updated_root: Path,
    snapshot: dict,
    changes: list[DetectedChange],
    changed_files: list[str],
    verification_results: list[dict],
) -> Path:
    proposal_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bundle_dir = proposal_root / timestamp
    candidate_dir = bundle_dir / "candidate"
    candidate_dir.mkdir(parents=True, exist_ok=True)

    (bundle_dir / "source_snapshot.json").write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (bundle_dir / "changes.json").write_text(
        json.dumps([serialize_change(change) for change in changes], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    proposal_patch = create_unified_diff(repo_root, updated_root, changed_files)
    (bundle_dir / "proposal.patch").write_text(proposal_patch, encoding="utf-8")
    (bundle_dir / "release_notes.md").write_text(build_release_notes(changes), encoding="utf-8")

    for relative_path in changed_files:
        destination = candidate_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(updated_root / relative_path, destination)

    report_lines = [
        "# TaxDE Rule Update Proposal",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Summary",
        "",
        f"- Changed files: {len(changed_files)}",
        f"- Detected rule/date changes: {len(changes)}",
        "",
        "## Detected Changes",
        "",
    ]
    if changes:
        for change in changes:
            report_lines.extend(
                [
                    (
                        f"- `{change.key}`: `{change.current_value}` -> `{change.proposed_value}` "
                        f"({change.severity}/{change.change_type})"
                    ),
                    f"  Source: {change.source_label}",
                    f"  URL: {change.source_url}",
                    f"  Derived from: `{change.derived_from}`",
                ]
            )
    else:
        report_lines.append("- No tracked changes detected.")

    report_lines.extend(["", "## Verification", ""])
    for result in verification_results:
        status = "PASS" if result["returncode"] == 0 else "FAIL"
        report_lines.append(f"- `{result['command']}` -> {status}")

    report_lines.extend(
        [
            "",
            "## Review Workflow",
            "",
            "1. Review `proposal.patch` and `candidate/`.",
            "2. Inspect `source_snapshot.json` and confirm the official-source matches.",
            "3. Review `release_notes.md` and `changes.json` for impact and scope.",
            "4. Approve the bundle explicitly:",
            "",
            f"```bash\npython3 scripts/tax_rule_updater.py approve --proposal-dir {bundle_dir} --reviewer <name>\n```",
            "",
            "5. After approval, apply with:",
            "",
            f"```bash\npython3 scripts/tax_rule_updater.py apply --proposal-dir {bundle_dir}\n```",
        ]
    )
    (bundle_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    verification_output = []
    for result in verification_results:
        verification_output.append(f"$ {result['command']}\n")
        if result["stdout"]:
            verification_output.append(result["stdout"])
        if result["stderr"]:
            verification_output.append(result["stderr"])
        verification_output.append("\n")
    (bundle_dir / "verification.log").write_text("".join(verification_output), encoding="utf-8")
    (bundle_dir / "proposal_manifest.json").write_text(
        json.dumps(
            {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "changed_files": changed_files,
                "detected_change_count": len(changes),
                "verification_passed": all(result["returncode"] == 0 for result in verification_results),
                "severity_summary": {
                    severity: sum(change.severity == severity for change in changes)
                    for severity in ("high", "medium", "low")
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return bundle_dir


def serialize_value(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def serialize_change(change: DetectedChange) -> dict:
    return {
        "key": change.key,
        "current_value": serialize_value(change.current_value),
        "proposed_value": serialize_value(change.proposed_value),
        "source_id": change.source_id,
        "source_label": change.source_label,
        "source_url": change.source_url,
        "derived_from": change.derived_from,
        "change_type": change.change_type,
        "severity": change.severity,
    }


def build_release_notes(changes: list[DetectedChange]) -> str:
    lines = [
        "# TaxDE update release notes",
        "",
        "This proposal updates bundled tax rules from tracked official sources.",
        "",
    ]
    if not changes:
        lines.append("- No tracked rule changes detected.")
        return "\n".join(lines) + "\n"

    for severity in ("high", "medium", "low"):
        grouped = [change for change in changes if change.severity == severity]
        if not grouped:
            continue
        lines.append(f"## {severity.title()} impact changes")
        lines.append("")
        for change in grouped:
            lines.append(
                f"- `{change.key}` ({change.change_type}): "
                f"`{serialize_value(change.current_value)}` -> `{serialize_value(change.proposed_value)}`"
            )
            lines.append(f"  Source: {change.source_label}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def print_change_summary(changes: list[DetectedChange]) -> None:
    if not changes:
        print("No tracked changes detected.")
        return
    for change in changes:
        print(
            f"{change.key}: {serialize_value(change.current_value)} -> "
            f"{serialize_value(change.proposed_value)} "
            f"[{change.severity}/{change.change_type}]"
        )
        print(f"  Source: {change.source_label}")
        print(f"  URL: {change.source_url}")


def build_proposal(fetcher: Callable[[str], str] = fetch_url_text) -> tuple[dict, list[DetectedChange], dict]:
    snapshot, source_lookup = collect_snapshot(fetcher=fetcher)
    proposed, derived_lookup = derive_proposed_updates(flatten_snapshot_values(snapshot), source_lookup)
    changes = detect_changes(proposed, derived_lookup)
    return snapshot, changes, proposed


def command_check(_: argparse.Namespace) -> int:
    _, changes, _ = build_proposal()
    print_change_summary(changes)
    return 0


def command_draft(args: argparse.Namespace) -> int:
    snapshot, changes, proposed = build_proposal()
    if not changes:
        print("No tracked changes detected. No proposal bundle created.")
        return 0

    with tempfile.TemporaryDirectory(prefix="taxde-update-") as temp_dir:
        temp_root = Path(temp_dir)
        worktree = copy_repo_to_temp(REPO_ROOT, temp_root)
        changed_files = apply_updates_to_repo(worktree, proposed)
        verification_results = run_verification(worktree)
        bundle_dir = write_proposal_bundle(
            proposal_root=Path(args.output_dir),
            repo_root=REPO_ROOT,
            updated_root=worktree,
            snapshot=snapshot,
            changes=changes,
            changed_files=changed_files,
            verification_results=verification_results,
        )

    print(f"Created proposal bundle: {bundle_dir}")
    print(f"Review report: {bundle_dir / 'report.md'}")
    print(f"Proposal patch: {bundle_dir / 'proposal.patch'}")
    return 0


def command_apply(args: argparse.Namespace) -> int:
    proposal_dir = Path(args.proposal_dir).resolve()
    candidate_dir = proposal_dir / "candidate"
    manifest_path = proposal_dir / "proposal_manifest.json"
    approval_path = proposal_dir / "review_approval.json"
    if not candidate_dir.exists():
        raise FileNotFoundError(f"No candidate directory found at {candidate_dir}")
    if not manifest_path.exists():
        raise FileNotFoundError(f"No proposal manifest found at {manifest_path}")
    if not approval_path.exists():
        raise PermissionError(
            "Proposal has not been approved. Run "
            "`python3 scripts/tax_rule_updater.py approve --proposal-dir ... --reviewer <name>` first."
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not manifest.get("verification_passed"):
        raise RuntimeError("Proposal verification did not pass. Fix the proposal before applying it.")

    applied = []
    for candidate in candidate_dir.rglob("*"):
        if not candidate.is_file():
            continue
        relative_path = candidate.relative_to(candidate_dir)
        destination = REPO_ROOT / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(candidate, destination)
        applied.append(str(relative_path))

    print(f"Applied {len(applied)} file(s) from {proposal_dir}")
    for relative_path in applied:
        print(f"- {relative_path}")
    print("Re-run verification before committing or merging.")
    return 0


def command_approve(args: argparse.Namespace) -> int:
    proposal_dir = Path(args.proposal_dir).resolve()
    manifest_path = proposal_dir / "proposal_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No proposal manifest found at {manifest_path}")

    approval_path = proposal_dir / "review_approval.json"
    approval_path.write_text(
        json.dumps(
            {
                "approved_at": datetime.now().isoformat(timespec="seconds"),
                "reviewer": args.reviewer,
                "notes": args.notes,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"Approved proposal bundle: {proposal_dir}")
    print(f"Approval record: {approval_path}")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Draft or apply safe TaxDE tax-rule update proposals.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Show tracked differences from official sources.")
    check.set_defaults(func=command_check)

    draft = subparsers.add_parser("draft", help="Create a reviewable proposal bundle.")
    draft.add_argument(
        "--output-dir",
        default=str(DEFAULT_PROPOSAL_ROOT),
        help="Directory that will receive the proposal bundle.",
    )
    draft.set_defaults(func=command_draft)

    approve_cmd = subparsers.add_parser("approve", help="Approve a reviewed proposal bundle.")
    approve_cmd.add_argument(
        "--proposal-dir",
        required=True,
        help="Existing proposal directory created by the draft command.",
    )
    approve_cmd.add_argument(
        "--reviewer",
        required=True,
        help="Short reviewer name recorded in the approval file.",
    )
    approve_cmd.add_argument(
        "--notes",
        default="",
        help="Optional reviewer notes.",
    )
    approve_cmd.set_defaults(func=command_approve)

    apply_cmd = subparsers.add_parser("apply", help="Apply a reviewed proposal bundle.")
    apply_cmd.add_argument(
        "--proposal-dir",
        required=True,
        help="Existing proposal directory created by the draft command.",
    )
    apply_cmd.set_defaults(func=command_apply)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
