"""
Archive and inspect official-source snapshots used by TaxDE.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from tax_rule_updater import build_normalized_snapshot_entries, collect_snapshot, flatten_snapshot_values
    from taxde_storage import get_source_snapshot_dir, load_json, save_json
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.dirname(__file__))
    from tax_rule_updater import build_normalized_snapshot_entries, collect_snapshot, flatten_snapshot_values
    from taxde_storage import get_source_snapshot_dir, load_json, save_json


def collect_official_source_snapshot() -> dict:
    snapshot, _ = collect_snapshot()
    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "sources": snapshot,
        "normalized_entries": build_normalized_snapshot_entries(snapshot),
        "flat_values": {
            key: (value.isoformat() if hasattr(value, "isoformat") else value)
            for key, value in flatten_snapshot_values(snapshot).items()
        },
    }


def archive_official_source_snapshot(snapshot: Optional[dict] = None) -> Path:
    payload = snapshot or collect_official_source_snapshot()
    path = get_source_snapshot_dir() / (
        datetime.now().strftime("%Y%m%d-%H%M%S") + ".json"
    )
    return save_json(path, payload)


def load_latest_source_snapshot() -> Optional[dict]:
    directory = get_source_snapshot_dir()
    candidates = sorted(directory.glob("*.json"))
    if not candidates:
        return None
    return load_json(candidates[-1], default=None)


if __name__ == "__main__":
    path = archive_official_source_snapshot()
    print(f"Archived source snapshot: {path}")
