"""
TaxDE claim engine.

Builds first-class claim objects from the stored profile, receipts, and bundled
rules, then persists them per tax year.
"""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Callable, Optional

try:
    from profile_manager import get_profile
    from refund_calculator import calculate_refund
    from tax_rules import get_tax_year_rules
    from taxde_storage import get_claims_path, save_json
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.dirname(__file__))
    from profile_manager import get_profile
    from refund_calculator import calculate_refund
    from tax_rules import get_tax_year_rules
    from taxde_storage import get_claims_path, save_json


def _lookup_missing_impact(result: dict, field_name: str) -> Optional[float]:
    for item in result.get("missing_data_impact", []):
        if item.get("field") == field_name:
            return round(float(item.get("potential_additional_refund", 0.0)), 2)
    return None


def _estimate_refund_effect(
    baseline_profile: dict,
    claim_id: str,
    modifier: Callable[[dict], None],
) -> float:
    profile = copy.deepcopy(baseline_profile)
    modifier(profile)
    baseline = calculate_refund(baseline_profile)["estimated_refund"]
    modified = calculate_refund(profile)["estimated_refund"]
    return round(max(0.0, baseline - modified), 2)


def _build_claim(
    tax_year: int,
    category: str,
    title: str,
    claim_id: str,
    status: str,
    amount_deductible: Optional[float],
    estimated_refund_effect: Optional[float],
    confidence: str,
    legal_basis: str,
    source_of_truth: str,
    evidence_present: list[str],
    evidence_missing: list[str],
    next_action: str,
    notes: str = "",
) -> dict:
    return {
        "id": claim_id,
        "tax_year": tax_year,
        "category": category,
        "title": title,
        "status": status,
        "amount_deductible": amount_deductible,
        "estimated_refund_effect": estimated_refund_effect,
        "confidence": confidence,
        "legal_basis": legal_basis,
        "source_of_truth": source_of_truth,
        "evidence_present": evidence_present,
        "evidence_missing": evidence_missing,
        "next_action": next_action,
        "notes": notes,
    }


def generate_claims(profile: Optional[dict] = None, persist: bool = True) -> dict:
    profile = profile or get_profile() or {}
    tax_year = profile.get("meta", {}).get("tax_year", datetime.now().year)
    rules = get_tax_year_rules(tax_year)
    baseline = calculate_refund(profile)

    employment = profile.get("employment", {})
    family = profile.get("family", {})
    housing = profile.get("housing", {})
    insurance = profile.get("insurance", {})
    special = profile.get("special", {})
    receipts = profile.get("current_year_receipts", [])

    claims: list[dict] = []

    def add_ready_claim(
        *,
        claim_id: str,
        category: str,
        title: str,
        amount: float,
        modifier: Callable[[dict], None],
        confidence: str,
        legal_basis: str,
        source_of_truth: str,
        evidence_present: list[str],
        evidence_missing: Optional[list[str]] = None,
        next_action: str,
        notes: str = "",
    ) -> None:
        claims.append(
            _build_claim(
                tax_year=tax_year,
                category=category,
                title=title,
                claim_id=claim_id,
                status="ready",
                amount_deductible=round(amount, 2),
                estimated_refund_effect=_estimate_refund_effect(profile, claim_id, modifier),
                confidence=confidence,
                legal_basis=legal_basis,
                source_of_truth=source_of_truth,
                evidence_present=evidence_present,
                evidence_missing=evidence_missing or [],
                next_action=next_action,
                notes=notes,
            )
        )

    emp_type = employment.get("type", "")
    is_employee = emp_type == "angestellter"

    # Homeoffice
    ho_days_pw = housing.get("homeoffice_days_per_week")
    if ho_days_pw is None and is_employee:
        claims.append(
            _build_claim(
                tax_year,
                "werbungskosten",
                "Homeoffice-Pauschale",
                "homeoffice",
                "needs_input",
                None,
                _lookup_missing_impact(baseline, "housing.homeoffice_days_per_week"),
                "likely",
                "§4 Abs. 5 Nr. 6b EStG / §9 Abs. 5 EStG",
                "missing_user_input",
                [],
                ["home-office days or weekly pattern"],
                "Confirm how many days per week you actually worked from home.",
            )
        )
    elif ho_days_pw:
        annual_days = min(int(ho_days_pw * 46), rules["homeoffice_max_days"])
        amount = min(annual_days * rules["homeoffice_tagespauschale"], rules["homeoffice_max_annual"])
        add_ready_claim(
            claim_id="homeoffice",
            category="werbungskosten",
            title="Homeoffice-Pauschale",
            amount=amount,
            modifier=lambda p: p.setdefault("housing", {}).update({"homeoffice_days_per_week": 0}),
            confidence="definitive",
            legal_basis="§4 Abs. 5 Nr. 6b EStG / §9 Abs. 5 EStG",
            source_of_truth="user_profile",
            evidence_present=[f"{annual_days} estimated home-office days"],
            next_action="Keep a day log or calendar note if the Finanzamt asks for support.",
        )

    # Commute
    commute_km = housing.get("commute_km")
    commute_days = housing.get("commute_days_per_year")
    if is_employee and not (commute_km and commute_days):
        claims.append(
            _build_claim(
                tax_year,
                "werbungskosten",
                "Pendlerpauschale",
                "commute",
                "needs_input",
                None,
                _lookup_missing_impact(baseline, "housing.commute_km"),
                "likely",
                "§9 Abs. 1 Nr. 4 EStG",
                "missing_user_input",
                [],
                ["commute distance and actual commute days"],
                "Confirm your one-way commute distance and actual office days.",
            )
        )
    elif commute_km and commute_days:
        short_km = min(commute_km, 20)
        long_km = max(commute_km - 20, 0)
        amount = commute_days * (
            short_km * rules["pendlerpauschale_short"] + long_km * rules["pendlerpauschale_long"]
        )
        add_ready_claim(
            claim_id="commute",
            category="werbungskosten",
            title="Pendlerpauschale",
            amount=amount,
            modifier=lambda p: p.setdefault("housing", {}).update({"commute_km": 0, "commute_days_per_year": 0}),
            confidence="definitive",
            legal_basis="§9 Abs. 1 Nr. 4 EStG",
            source_of_truth="user_profile",
            evidence_present=[f"{commute_km} km one-way", f"{commute_days} commute days"],
            next_action="Use actual commute days, not calendar working days.",
        )

    # Equipment / education / donations from receipts
    for receipt_category, claim_id, title, category, basis in (
        ("equipment", "equipment", "Arbeitsmittel", "werbungskosten", "§9 Abs. 1 Nr. 6 EStG"),
        ("fortbildung", "fortbildung", "Fortbildungskosten", "werbungskosten", "§9 Abs. 1 Nr. 6 EStG"),
        ("donation", "donation", "Spenden", "sonderausgaben", "§10b EStG"),
    ):
        filtered = [r for r in receipts if r.get("category") == receipt_category]
        if not filtered:
            continue
        amount = sum(float(r.get("deductible_amount") or 0.0) for r in filtered)
        if amount <= 0:
            continue

        def _modifier(p: dict, category_name: str = receipt_category) -> None:
            p["current_year_receipts"] = [
                receipt for receipt in p.get("current_year_receipts", [])
                if receipt.get("category") != category_name
            ]

        add_ready_claim(
            claim_id=claim_id,
            category=category,
            title=title,
            amount=amount,
            modifier=_modifier,
            confidence="definitive" if receipt_category != "equipment" else "likely",
            legal_basis=basis,
            source_of_truth="receipt_log",
            evidence_present=[f"{len(filtered)} receipt(s) logged"],
            next_action="Keep the invoice or receipt with a short business-purpose note.",
        )

    if is_employee and not any(r.get("category") == "equipment" for r in receipts):
        claims.append(
            _build_claim(
                tax_year,
                "werbungskosten",
                "Arbeitsmittel",
                "equipment_opportunity",
                "detected",
                None,
                None,
                "likely",
                "§9 Abs. 1 Nr. 6 EStG",
                "profile_inference",
                [],
                ["equipment receipts if you bought work gear"],
                "Check whether you bought a laptop, monitor, desk, chair, books, or training this year.",
            )
        )

    # Childcare
    children = family.get("children", [])
    childcare_claims = []
    for idx, child in enumerate(children, start=1):
        birth_year = child.get("birth_year")
        age = tax_year - birth_year if birth_year else 99
        if age >= 14 or not child.get("kita"):
            continue
        annual_cost = child.get("kita_annual_cost")
        if annual_cost:
            childcare_claims.append(min(annual_cost * rules["kinderbetreuung_pct"], rules["kinderbetreuung_max"]))
        else:
            claims.append(
                _build_claim(
                    tax_year,
                    "sonderausgaben",
                    f"Kinderbetreuungskosten (child {idx})",
                    f"childcare_child_{idx}",
                    "needs_evidence",
                    None,
                    None,
                    "definitive",
                    "§10 Abs. 1 Nr. 5 EStG",
                    "partial_profile",
                    [f"child {idx} marked as childcare relevant"],
                    ["annual childcare cost and proof of bank transfer"],
                    "Add annual childcare cost and keep the invoice plus payment proof.",
                )
            )
    if childcare_claims:
        amount = sum(childcare_claims)
        add_ready_claim(
            claim_id="childcare",
            category="sonderausgaben",
            title="Kinderbetreuungskosten",
            amount=amount,
            modifier=lambda p: [
                child.update({"kita_annual_cost": 0}) for child in p.get("family", {}).get("children", [])
            ],
            confidence="definitive",
            legal_basis="§10 Abs. 1 Nr. 5 EStG",
            source_of_truth="user_profile",
            evidence_present=[f"{len(childcare_claims)} childcare amount(s) entered"],
            next_action="Keep the annual childcare invoice and proof of bank transfer.",
        )

    # Riester / Ruerup / bAV / union dues / disability
    if insurance.get("riester"):
        contrib = float(insurance.get("riester_contribution") or 0.0)
        if contrib:
            add_ready_claim(
                claim_id="riester",
                category="sonderausgaben",
                title="Riester contribution",
                amount=min(contrib, rules["riester_max"]),
                modifier=lambda p: p.setdefault("insurance", {}).update({"riester_contribution": 0}),
                confidence="definitive",
                legal_basis="§10a EStG",
                source_of_truth="user_profile",
                evidence_present=["Riester contribution entered"],
                next_action="Keep the provider statement for Anlage AV.",
            )
        else:
            claims.append(
                _build_claim(
                    tax_year,
                    "sonderausgaben",
                    "Riester contribution",
                    "riester",
                    "needs_evidence",
                    None,
                    None,
                    "definitive",
                    "§10a EStG",
                    "partial_profile",
                    ["Riester marked as active"],
                    ["annual provider contribution statement"],
                    "Add your annual Riester contribution or the provider statement.",
                )
            )

    if insurance.get("ruerup"):
        contrib = float(insurance.get("ruerup_contribution") or 0.0)
        if contrib:
            cap = rules.get("ruerup_max_single")
            add_ready_claim(
                claim_id="ruerup",
                category="sonderausgaben",
                title="Ruerup / Basisrente",
                amount=contrib if cap is None else min(contrib, cap),
                modifier=lambda p: p.setdefault("insurance", {}).update({"ruerup_contribution": 0}),
                confidence="likely" if cap is None else "definitive",
                legal_basis="§10 Abs. 1 Nr. 2b EStG",
                source_of_truth="user_profile",
                evidence_present=["Ruerup contribution entered"],
                next_action="Keep the annual provider statement.",
                notes="The annual cap may require official verification if the bundled year does not include it.",
            )
        else:
            claims.append(
                _build_claim(
                    tax_year,
                    "sonderausgaben",
                    "Ruerup / Basisrente",
                    "ruerup",
                    "needs_evidence",
                    None,
                    None,
                    "likely",
                    "§10 Abs. 1 Nr. 2b EStG",
                    "partial_profile",
                    ["Ruerup marked as active"],
                    ["annual contribution amount"],
                    "Add the annual Ruerup contribution amount.",
                )
            )

    if insurance.get("bav"):
        contrib = float(insurance.get("bav_contribution") or 0.0)
        if contrib:
            add_ready_claim(
                claim_id="bav",
                category="vorsorge",
                title="bAV salary conversion",
                amount=min(contrib, rules["bav_4pct_bbg"]),
                modifier=lambda p: p.setdefault("insurance", {}).update({"bav_contribution": 0}),
                confidence="definitive",
                legal_basis="§3 Nr. 63 EStG",
                source_of_truth="user_profile",
                evidence_present=["bAV contribution entered"],
                next_action="Confirm whether the contribution is already reflected in the gross salary figure.",
            )

    if special.get("gewerkschaft_beitrag"):
        amount = float(special.get("gewerkschaft_beitrag") or 0.0)
        add_ready_claim(
            claim_id="union_dues",
            category="werbungskosten",
            title="Gewerkschaftsbeiträge",
            amount=amount,
            modifier=lambda p: p.setdefault("special", {}).update({"gewerkschaft_beitrag": 0}),
            confidence="definitive",
            legal_basis="§9 Abs. 1 Nr. 3d EStG",
            source_of_truth="user_profile",
            evidence_present=["annual union dues entered"],
            next_action="Keep the annual union statement.",
        )

    disability_grade = int(special.get("disability_grade") or 0)
    if disability_grade >= 20:
        grade = (disability_grade // 10) * 10
        amount = rules["behindertenpauschbetrag"].get(grade, 0)
        add_ready_claim(
            claim_id="disability_allowance",
            category="aussergewoehnliche_belastungen",
            title="Behinderten-Pauschbetrag",
            amount=amount,
            modifier=lambda p: p.setdefault("special", {}).update({"disability_grade": 0}),
            confidence="definitive",
            legal_basis="§33b EStG",
            source_of_truth="user_profile",
            evidence_present=[f"disability grade {disability_grade}"],
            next_action="Keep the disability certificate / official proof.",
        )

    claims.sort(
        key=lambda item: (
            {"ready": 0, "needs_evidence": 1, "needs_input": 2, "detected": 3}.get(item["status"], 9),
            -(item["estimated_refund_effect"] or 0.0),
            item["title"],
        )
    )

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "tax_year": tax_year,
        "claim_count": len(claims),
        "claims": claims,
    }
    if persist:
        save_json(get_claims_path(tax_year), payload)
    return payload


if __name__ == "__main__":
    result = generate_claims()
    print(f"Generated {result['claim_count']} claim(s) for {result['tax_year']}.")
