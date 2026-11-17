"""
Smart Coupon AI Agent - Core Coupon Engine
Handles coupon validation, discount calculation, comparisons, and recommendation reasoning.
"""

from datetime import datetime, date
import json
import os
from typing import Dict, List, Optional, Tuple, Any


def load_coupons(filepath: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load coupon database from JSON file.
    If filepath is not provided, defaults to data/coupons.json relative to this file.
    """
    if filepath is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(base_dir, "data", "coupons.json")

    if not os.path.exists(filepath):
        return []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading coupons from {filepath}: {e}")
        return []


def load_fallback_offers(filepath: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load alternative/fallback offers (bank cashbacks, UPI offers, free shipping) from JSON file.
    """
    if filepath is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(base_dir, "data", "fallback_offers.json")

    if not os.path.exists(filepath):
        return []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading fallback offers from {filepath}: {e}")
        return []


def parse_date(date_str: str) -> Optional[date]:
    """Safely parse YYYY-MM-DD date string to a date object."""
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except Exception:
        return None


def is_coupon_expired(coupon: Dict[str, Any], current_date: Optional[date] = None) -> Tuple[bool, str]:
    """
    Check if a coupon is expired based on current_date (defaults to today).
    Returns (is_expired, formatted_expiry_str).
    """
    if current_date is None:
        current_date = date.today()

    expiry_str = coupon.get("expiry_date", "")
    exp_date = parse_date(expiry_str)

    if exp_date is None:
        return False, expiry_str

    if exp_date < current_date:
        return True, expiry_str
    return False, expiry_str


def validate_coupon(
    coupon: Dict[str, Any],
    customer_name: str,
    category: str,
    platform: str,
    bill_amount: float,
    current_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Validate a coupon against eligibility criteria:
    1. Expiration date check
    2. Category eligibility
    3. Platform eligibility
    4. Minimum spend threshold

    Returns a dictionary detailing validation status and human-friendly reasons.
    """
    if current_date is None:
        current_date = date.today()

    code = coupon.get("code", "UNKNOWN")
    min_purchase = float(coupon.get("min_purchase", 0))
    raw_cats = coupon.get("applicable_categories") or coupon.get("applicable_category") or []
    if isinstance(raw_cats, str):
        applicable_categories = [raw_cats]
    else:
        applicable_categories = list(raw_cats)
    applicable_platforms = coupon.get("applicable_platforms", [])

    # 1. Expiry Check
    expired, expiry_str = is_coupon_expired(coupon, current_date)
    if expired:
        return {
            "is_valid": False,
            "status_code": "EXPIRED",
            "badge": "🔴 Expired",
            "reason": f"Coupon '{code}' expired on {expiry_str}.",
            "shortfall": 0.0,
            "category_match": False,
            "platform_match": False,
            "min_spend_met": bill_amount >= min_purchase
        }

    # 2. Category Check
    category_clean = category.strip()
    is_category_eligible = (
        "All" in applicable_categories or
        category_clean in applicable_categories or
        any(cat.lower() == category_clean.lower() for cat in applicable_categories)
    )

    if not is_category_eligible:
        allowed = ", ".join(applicable_categories)
        return {
            "is_valid": False,
            "status_code": "CATEGORY_MISMATCH",
            "badge": "⚠️ Wrong Category",
            "reason": f"Only valid on {allowed} (your cart is {category_clean}).",
            "shortfall": 0.0,
            "category_match": False,
            "platform_match": True,
            "min_spend_met": bill_amount >= min_purchase
        }

    # 3. Platform Check (if specified and not 'General / Other')
    platform_clean = platform.strip()
    is_platform_eligible = True
    if applicable_platforms and "All" not in applicable_platforms:
        if platform_clean not in ["General / Other", "Other", "Any"]:
            is_platform_eligible = (
                platform_clean in applicable_platforms or
                any(p.lower() == platform_clean.lower() for p in applicable_platforms)
            )

    if not is_platform_eligible:
        allowed_platforms = ", ".join(applicable_platforms)
        return {
            "is_valid": False,
            "status_code": "PLATFORM_MISMATCH",
            "badge": "⚠️ Wrong Platform",
            "reason": f"Only valid on {allowed_platforms} (selected: {platform_clean}).",
            "shortfall": 0.0,
            "category_match": True,
            "platform_match": False,
            "min_spend_met": bill_amount >= min_purchase
        }

    # 4. Minimum Spend Check
    if bill_amount < min_purchase:
        shortfall = round(min_purchase - bill_amount, 2)
        return {
            "is_valid": False,
            "status_code": "BELOW_MIN_PURCHASE",
            "badge": "⏳ Min Spend Not Met",
            "reason": f"Requires minimum purchase of ₹{min_purchase:,.2f}. Add ₹{shortfall:,.2f} more to qualify.",
            "shortfall": shortfall,
            "category_match": True,
            "platform_match": True,
            "min_spend_met": False
        }

    # All criteria passed!
    return {
        "is_valid": True,
        "status_code": "VALID",
        "badge": "🟢 Eligible",
        "reason": f"Eligible! Meets all conditions (Min spend: ₹{min_purchase:,.2f}, Category: {category_clean}).",
        "shortfall": 0.0,
        "category_match": True,
        "platform_match": True,
        "min_spend_met": True
    }


def calculate_discount(coupon: Dict[str, Any], bill_amount: float) -> Dict[str, Any]:
    """
    Calculate the actual discount and net bill for an eligible coupon,
    accurately respecting the maximum discount cap.
    """
    discount_pct = float(coupon.get("discount_percentage", 0))
    max_discount = float(coupon.get("max_discount", float("inf")))

    # Calculate theoretical percentage discount
    raw_discount = round(bill_amount * (discount_pct / 100.0), 2)

    # Apply maximum discount cap
    is_capped = raw_discount >= max_discount
    actual_discount = round(min(raw_discount, max_discount), 2)

    # Final bill cannot be negative
    final_bill = round(max(0.0, bill_amount - actual_discount), 2)
    effective_savings_pct = round((actual_discount / bill_amount) * 100.0, 1) if bill_amount > 0 else 0.0

    return {
        "raw_discount": raw_discount,
        "actual_discount": actual_discount,
        "is_capped": is_capped,
        "max_discount": max_discount,
        "discount_percentage": discount_pct,
        "original_bill": bill_amount,
        "final_bill": final_bill,
        "effective_savings_percentage": effective_savings_pct
    }


def generate_recommendation_reason(
    best_coupon: Dict[str, Any],
    best_discount_info: Dict[str, Any],
    runner_up: Optional[Dict[str, Any]] = None,
    runner_up_discount_info: Optional[Dict[str, Any]] = None,
    total_eligible: int = 1
) -> str:
    """
    Generate an intelligent, AI-agent style explanation of why this coupon was chosen.
    """
    code = best_coupon.get("code")
    pct = best_discount_info.get("discount_percentage")
    actual_save = best_discount_info.get("actual_discount")
    max_disc = best_discount_info.get("max_discount")
    is_capped = best_discount_info.get("is_capped")
    effective_pct = best_discount_info.get("effective_savings_percentage")

    reasons = []

    # Main savings statement
    if is_capped:
        reasons.append(
            f"Code **{code}** gives you the maximum possible discount of **₹{actual_save:,.2f}** "
            f"(the {pct}% discount hit the high cap limit of ₹{max_disc:,.2f})."
        )
    else:
        reasons.append(
            f"Code **{code}** yields the absolute highest savings of **₹{actual_save:,.2f}** "
            f"({pct}% off your bill)."
        )

    # Comparison with competition
    if runner_up and runner_up_discount_info:
        r_code = runner_up.get("code")
        r_save = runner_up_discount_info.get("actual_discount")
        diff = round(actual_save - r_save, 2)
        if diff > 0:
            reasons.append(
                f"It beats the next best option (**{r_code}** with ₹{r_save:,.2f}) by an extra **₹{diff:,.2f}** in your pocket."
            )
        else:
            reasons.append(
                f"Tied in highest cash savings with **{r_code}**, but chosen for best overall value terms."
            )
    elif total_eligible == 1:
        reasons.append(
            f"This is the sole verified eligible coupon that fully matches your cart criteria, unlocking an effective **{effective_pct}%** reduction on your total bill."
        )
    else:
        reasons.append(
            f"Out of {total_eligible} eligible coupons evaluated, this provides the greatest net price reduction."
        )

    return " ".join(reasons)


def find_best_coupon(
    coupons: List[Dict[str, Any]],
    category: str,
    platform: str,
    bill_amount: float,
    customer_name: str = "Valued Customer",
    current_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Evaluate all coupons in database:
    - Separates into eligible and ineligible
    - Calculates accurate discount for all eligible
    - Ranks and recommends the single best coupon
    - Formulates transparent AI recommendation reasoning
    - Provides near-miss tips for ineligible coupons
    """
    if current_date is None:
        current_date = date.today()

    evaluated_eligible: List[Dict[str, Any]] = []
    evaluated_ineligible: List[Dict[str, Any]] = []

    for coupon in coupons:
        val_result = validate_coupon(
            coupon=coupon,
            customer_name=customer_name,
            category=category,
            platform=platform,
            bill_amount=bill_amount,
            current_date=current_date
        )

        item = {
            "coupon": coupon,
            "validation": val_result
        }

        if val_result["is_valid"]:
            calc = calculate_discount(coupon, bill_amount)
            item["calculation"] = calc
            evaluated_eligible.append(item)
        else:
            evaluated_ineligible.append(item)

    # Sort eligible by actual_discount descending, then discount_percentage descending
    evaluated_eligible.sort(
        key=lambda x: (
            x["calculation"]["actual_discount"],
            x["calculation"]["discount_percentage"]
        ),
        reverse=True
    )

    if evaluated_eligible:
        best_item = evaluated_eligible[0]
        runner_up_item = evaluated_eligible[1] if len(evaluated_eligible) > 1 else None

        reason = generate_recommendation_reason(
            best_coupon=best_item["coupon"],
            best_discount_info=best_item["calculation"],
            runner_up=runner_up_item["coupon"] if runner_up_item else None,
            runner_up_discount_info=runner_up_item["calculation"] if runner_up_item else None,
            total_eligible=len(evaluated_eligible)
        )

        return {
            "found": True,
            "best_coupon": best_item["coupon"],
            "calculation": best_item["calculation"],
            "recommendation_reason": reason,
            "eligible_coupons": evaluated_eligible,
            "ineligible_coupons": evaluated_ineligible,
            "near_misses": find_near_miss_coupons(evaluated_ineligible, bill_amount)
        }
    else:
        # No eligible coupon found
        return {
            "found": False,
            "best_coupon": None,
            "calculation": None,
            "recommendation_reason": (
                f"No standard coupon met your criteria for {category} on {platform} with a cart of ₹{bill_amount:,.2f}. "
                "See available alternative offers and unlockable coupons below!"
            ),
            "eligible_coupons": [],
            "ineligible_coupons": evaluated_ineligible,
            "near_misses": find_near_miss_coupons(evaluated_ineligible, bill_amount)
        }


def find_near_miss_coupons(ineligible_items: List[Dict[str, Any]], bill_amount: float) -> List[Dict[str, Any]]:
    """
    Identify coupons that were ineligible SOLELY because the bill was below the minimum spend,
    and offer actionable shopping tips (e.g., 'Add ₹80 to save ₹200').
    """
    near_misses = []
    for item in ineligible_items:
        val = item["validation"]
        coupon = item["coupon"]

        # If it failed only due to min purchase (category & platform match, not expired)
        if (
            val["status_code"] == "BELOW_MIN_PURCHASE" and
            val["category_match"] and
            val["platform_match"]
        ):
            shortfall = val["shortfall"]
            min_purchase = float(coupon.get("min_purchase", 0))
            potential_calc = calculate_discount(coupon, min_purchase)

            near_misses.append({
                "coupon": coupon,
                "shortfall": shortfall,
                "min_purchase": min_purchase,
                "potential_discount": potential_calc["actual_discount"],
                "tip": (
                    f"Add items worth **₹{shortfall:,.2f}** more to unlock **{coupon.get('code')}** "
                    f"and save up to **₹{potential_calc['actual_discount']:,.2f}**!"
                )
            })

    # Sort near misses by lowest shortfall first
    near_misses.sort(key=lambda x: x["shortfall"])
    return near_misses


def evaluate_fallback_offers(
    fallback_offers: List[Dict[str, Any]],
    category: str,
    platform: str,
    bill_amount: float
) -> List[Dict[str, Any]]:
    """
    Filter and compute benefits for alternative/fallback offers (card discounts, UPI cashback, etc.).
    """
    applicable = []
    for offer in fallback_offers:
        min_p = float(offer.get("min_purchase", 0))
        cats = offer.get("applicable_categories", [])

        # Check category
        if "All" not in cats and category not in cats and not any(c.lower() == category.lower() for c in cats):
            continue

        # Check minimum spend
        if bill_amount >= min_p:
            disc_type = offer.get("discount_type", "percentage")
            disc_val = float(offer.get("discount_value", 0))
            max_disc = float(offer.get("max_discount", float("inf")))

            if disc_type == "percentage":
                est_savings = min(bill_amount * (disc_val / 100.0), max_disc)
            else:
                est_savings = min(disc_val, max_disc)

            applicable.append({
                "offer": offer,
                "estimated_savings": round(est_savings, 2),
                "is_qualified": True,
                "status": "Ready to Use"
            })
        else:
            shortfall = round(min_p - bill_amount, 2)
            applicable.append({
                "offer": offer,
                "estimated_savings": 0.0,
                "is_qualified": False,
                "shortfall": shortfall,
                "status": f"Spend ₹{shortfall:,.2f} more to unlock"
            })

    # Qualified offers first, sorted by estimated savings descending
    applicable.sort(key=lambda x: (x["is_qualified"], x["estimated_savings"]), reverse=True)
    return applicable
