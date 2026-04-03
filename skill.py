"""
Finance Assistant Skill — entry point for Claude Code.

This file is the skill entry point that was missing in the original TaxDE.
It bootstraps the scripts/ directory and provides the initial session hook.
"""

import sys
import os

# Ensure scripts/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))

from profile_manager import get_profile, display_profile


def _setup_security_defaults() -> None:
    """Run once-per-session security hygiene: gitignore guard + permission check."""
    try:
        from data_safety import ensure_gitignore_protection, check_permissions
        ensure_gitignore_protection()
        result = check_permissions()
        if result.get("status") == "insecure":
            # Non-fatal — just surface a hint in the session log
            print(
                "[Finance Assistant] Warning: some .finance/ files have loose permissions. "
                "Run harden_permissions() to restrict access to your OS user only."
            )
    except Exception:
        pass  # Security helpers must never crash the skill


def main() -> str:
    """Called at skill load time. Returns initial greeting or status."""
    _setup_security_defaults()
    profile = get_profile()

    if not profile or not profile.get("meta", {}).get("created"):
        return (
            "Welcome to Finance Assistant! I help with budgeting, savings goals, investments, "
            "debt optimization, taxes, insurance, and net worth tracking.\n\n"
            "Your data lives only in .finance/ on your machine — nothing is ever uploaded. "
            "You can encrypt it, export it, or delete it completely at any time.\n\n"
            "To get started: what's your employment situation and roughly what do you earn? "
            "I'm optimised for Germany (full tax rules for 2024-2026) but work for any country "
            "for budgeting, investments, and debt — just with limited tax support outside Germany."
        )

    profile_display = display_profile(compact=True)

    # Surface proactive alerts after the profile summary
    try:
        from session_alerts import get_session_alerts, format_alerts
        alerts = get_session_alerts(profile)
        if alerts:
            return profile_display + "\n\n" + format_alerts(alerts)
    except Exception:
        pass  # Alerts must never crash the skill

    return profile_display


if __name__ == "__main__":
    print(main())
