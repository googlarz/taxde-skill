"""
Shared project-local storage helpers for TaxDE.

TaxDE keeps runtime state in the active project's `.taxde/` directory.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


PROFILE_DIRNAME = ".taxde"


def get_project_dir() -> Path:
    project_dir = (
        os.environ.get("TAXDE_PROJECT_DIR")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or os.getcwd()
    )
    return Path(project_dir).expanduser().resolve()


def get_taxde_dir() -> Path:
    return get_project_dir() / PROFILE_DIRNAME


def ensure_taxde_dir() -> Path:
    path = get_taxde_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_subdir(*parts: str) -> Path:
    path = ensure_taxde_dir().joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_profile_path() -> Path:
    explicit = os.environ.get("TAXDE_PROFILE_PATH")
    if explicit:
        return Path(explicit).expanduser().resolve()
    return ensure_taxde_dir() / "taxde_profile.json"


def get_claims_path(tax_year: int) -> Path:
    return ensure_subdir("claims") / f"{tax_year}.json"


def get_workspace_path(tax_year: int) -> Path:
    return ensure_subdir("workspace") / f"{tax_year}.json"


def get_filing_pack_path(tax_year: int) -> Path:
    return ensure_subdir("workspace") / f"{tax_year}-filing-pack.json"


def get_output_suite_path(tax_year: int) -> Path:
    return ensure_subdir("workspace") / f"{tax_year}-outputs.json"


def get_source_snapshot_dir() -> Path:
    return ensure_subdir("source_snapshots")


def get_proposal_dir() -> Path:
    return ensure_subdir("proposals")


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    return path
