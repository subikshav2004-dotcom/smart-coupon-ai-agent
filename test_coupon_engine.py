"""
Unit tests for Smart Coupon AI Agent logic.
Can be executed with: python test_coupon_engine.py
"""

import unittest
from datetime import date
from coupon_engine import (
    load_coupons,
    load_fallback_offers,
    validate_coupon,
    calculate_discount,
    find_best_coupon,
    evaluate_fallback_offers
)


class TestCouponEngine(unittest.TestCase):

    def setUp(self):
        self.coupons = load_coupons()
        self.fallback_offers = load_fallback_offers()
        # Reference test date to ensure consistent results
        self.test_date = date(2026, 11, 16)

    def test_coupon_database_loaded(self):
        """Verify coupons and fallback offers are loaded from JSON."""
        self.assertGreater(len(self.coupons), 0, "Coupons database should not be empty")
        self.assertGreater(len(self.fallback_offers), 0, "Fallback offers should not be empty")

    def test_expired_coupon_rejected(self):
        """Verify expired coupons are never validated as eligible."""
        expired_coupon = {
            "code": "OLD20",
            "discount_percentage": 20,
            "max_discount": 500,
            "min_purchase": 500,
            "applicable_categories": ["Electronics"],
            "applicable_platforms": ["Amazon"],
            "expiry_date": "2024-01-01"
        }
        res = validate_coupon(
            coupon=expired_coupon,
            customer_name="Alice",
            category="Electronics",
            platform="Amazon",
            bill_amount=1000.0,
            current_date=self.test_date
        )
        self.assertFalse(res["is_valid"], "Expired coupon must not be valid")
        self.assertEqual(res["status_code"], "EXPIRED")

    def test_category_mismatch_rejected(self):
        """Verify coupon is rejected if category does not match."""
        food_coupon = {
            "code": "EATS20",
            "discount_percentage": 20,
            "max_discount": 200,
            "min_purchase": 300,
            "applicable_categories": ["Food"],
            "applicable_platforms": ["Swiggy"],
            "expiry_date": "2027-12-31"
        }
        res = validate_coupon(
            coupon=food_coupon,
            customer_name="Bob",
            category="Electronics",
            platform="Swiggy",
            bill_amount=500.0,
            current_date=self.test_date
        )
        self.assertFalse(res["is_valid"], "Category mismatch must be rejected")
        self.assertEqual(res["status_code"], "CATEGORY_MISMATCH")

    def test_min_purchase_shortfall(self):
        """Verify coupon is rejected when bill is below minimum purchase threshold."""
        coupon = {
            "code": "BIGSAVE",
            "discount_percentage": 20,
            "max_discount": 1000,
            "min_purchase": 2000,
            "applicable_categories": ["Electronics"],
            "applicable_platforms": ["Amazon"],
            "expiry_date": "2027-12-31"
        }
        res = validate_coupon(
            coupon=coupon,
            customer_name="Charlie",
            category="Electronics",
            platform="Amazon",
            bill_amount=1500.0,
            current_date=self.test_date
        )
        self.assertFalse(res["is_valid"], "Must be rejected if bill < min_purchase")
        self.assertEqual(res["status_code"], "BELOW_MIN_PURCHASE")
        self.assertEqual(res["shortfall"], 500.0)

    def test_discount_calculation_with_cap(self):
        """Verify discount percentage and maximum discount cap calculation."""
        # 50% off up to 1000. For bill of 3000, 50% is 1500, but cap is 1000.
        coupon = {
            "code": "HALFPRICE",
            "discount_percentage": 50,
            "max_discount": 1000,
            "min_purchase": 500,
            "applicable_categories": ["Fashion"],
            "expiry_date": "2027-12-31"
        }
        calc = calculate_discount(coupon, 3000.0)
        self.assertEqual(calc["raw_discount"], 1500.0)
        self.assertEqual(calc["actual_discount"], 1000.0)
        self.assertTrue(calc["is_capped"])
        self.assertEqual(calc["final_bill"], 2000.0)

        # For bill of 1000, 50% is 500 (< cap 1000).
        calc2 = calculate_discount(coupon, 1000.0)
        self.assertEqual(calc2["actual_discount"], 500.0)
        self.assertFalse(calc2["is_capped"])
        self.assertEqual(calc2["final_bill"], 500.0)

    def test_find_best_coupon_picks_highest_savings(self):
        """Verify that find_best_coupon picks the one with highest actual savings."""
        result = find_best_coupon(
            coupons=self.coupons,
            category="Electronics",
            platform="Amazon",
            bill_amount=10000.0,
            customer_name="Dana",
            current_date=self.test_date
        )
        self.assertTrue(result["found"])
        best = result["best_coupon"]
        calc = result["calculation"]
        # In electronics for 10000:
        # ELECTRO20: 20% of 10000 = 2000, cap 1500 -> 1500
        # MEGACHIP30: 30% of 10000 = 3000, cap 2500 -> 2500
        # FESTIVE35: 35% of 10000 = 3500, cap 2000 -> 2000
        # UNIVERSAL10: 10% of 10000 = 1000, cap 500 -> 500
        # Best should be MEGACHIP30 with discount of 2500!
        self.assertEqual(best["code"], "MEGACHIP30")
        self.assertEqual(calc["actual_discount"], 2500.0)
        self.assertEqual(calc["final_bill"], 7500.0)
        self.assertIn("MEGACHIP30", result["recommendation_reason"])

    def test_fallback_offers_when_no_coupon_valid(self):
        """Verify fallback offers are returned when no coupons qualify."""
        # Cart of 150 for Food: below FOODIE15 (min 200) and YUMMY40 (min 300)
        result = find_best_coupon(
            coupons=self.coupons,
            category="Food",
            platform="Swiggy",
            bill_amount=150.0,
            customer_name="Eve",
            current_date=self.test_date
        )
        self.assertFalse(result["found"])
        self.assertIsNone(result["best_coupon"])

        fallbacks = evaluate_fallback_offers(
            self.fallback_offers,
            category="Food",
            platform="Swiggy",
            bill_amount=150.0
        )
        self.assertGreater(len(fallbacks), 0, "Should evaluate fallback offers")


if __name__ == "__main__":
    unittest.main()
