"""
Smart Coupon AI Agent - AI Recommender & Explanation Module
Integrates the modern Google Gen AI Python SDK with an intelligent model cascade
(gemini-3.5-flash-lite, gemini-3.8-flash, gemini-3.1-flash-lite) to produce
personalized, intelligent coupon advice and checkout optimization.
Loads GEMINI_API_KEY securely from .env and includes seamless offline rule-based fallback.
"""

import json
import os
from typing import Dict, List, Optional, Any, Tuple
from dotenv import load_dotenv

# Load environment variables from .env file securely
load_dotenv()

# Active, supported Gemini Flash models in priority order
DEFAULT_MODEL_CASCADE = [
    "gemini-3.5-flash-lite",  # Fast, active Flash model (sub-second response)
    "gemini-3.8-flash",       # Modern flagship Flash model
    "gemini-3.1-flash-lite",  # Secondary active lightweight Flash fallback
]


class AIRecommender:
    """
    AI-powered recommendation and reasoning assistant.
    Combines the modern Google Gen AI Python SDK with a high-precision
    offline rule-based reasoning engine for 100% resilience.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        use_gemini: bool = True,
        model_name: Optional[str] = None,
        model_cascade: Optional[List[str]] = None
    ):
        # Reload .env in case it was updated recently
        load_dotenv()
        
        # Securely retrieve API key without exposing it
        env_key = os.getenv("GEMINI_API_KEY", "")
        self.api_key = (api_key if api_key is not None else env_key).strip()
        
        # Configure model cascade
        if model_cascade:
            self.models_to_try = list(model_cascade)
        elif model_name:
            self.models_to_try = [model_name] + [m for m in DEFAULT_MODEL_CASCADE if m != model_name]
        else:
            self.models_to_try = list(DEFAULT_MODEL_CASCADE)

        self.primary_model = self.models_to_try[0]
        self.use_gemini = use_gemini and bool(self.api_key)
        self._last_error: Optional[str] = None
        self._last_used_model: Optional[str] = None

    def _sanitize(self, msg: str) -> str:
        """Helper to sanitize any text and remove any accidental API key tokens."""
        if self.api_key and self.api_key in msg:
            return msg.replace(self.api_key, "[REDACTED_API_KEY]")
        return msg

    def get_status(self) -> Dict[str, Any]:
        """
        Check the current status of Gemini AI integration safely.
        Never exposes the API key string.
        """
        has_key = bool(self.api_key)
        masked_indicator = "Configured (••••••••)" if has_key else "Not detected in .env"
        
        return {
            "has_key": has_key,
            "key_display": masked_indicator,
            "use_gemini": self.use_gemini,
            "primary_model": self.primary_model,
            "cascade": self.models_to_try,
            "mode": f"✨ Google Gemini AI ({self.primary_model})" if (self.use_gemini and has_key) else "Offline Smart Rule Engine"
        }

    def generate_recommendation_summary(
        self,
        customer_name: str,
        category: str,
        platform: str,
        bill_amount: float,
        best_coupon: Optional[Dict[str, Any]],
        calculation: Optional[Dict[str, Any]],
        runner_up: Optional[Dict[str, Any]] = None,
        runner_up_calculation: Optional[Dict[str, Any]] = None,
        total_eligible_count: int = 0,
        near_misses: Optional[List[Dict[str, Any]]] = None,
        fallback_offers: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Produce a comprehensive AI recommendation report.
        If Gemini is enabled and configured, queries the Gemini Flash model cascade.
        If all models fail or Gemini is disabled, seamlessly falls back
        to the built-in rule-based AI engine.
        """
        customer = customer_name.strip() if customer_name and customer_name.strip() else "Shopper"

        # 1. Attempt Gemini AI explanation if enabled and key is present
        if self.use_gemini and self.api_key:
            gemini_result = self._call_gemini_explainer(
                customer=customer,
                category=category,
                platform=platform,
                bill_amount=bill_amount,
                best_coupon=best_coupon,
                calculation=calculation,
                runner_up=runner_up,
                runner_up_calculation=runner_up_calculation,
                total_eligible_count=total_eligible_count,
                near_misses=near_misses or [],
                fallback_offers=fallback_offers or []
            )
            if gemini_result:
                return gemini_result

        # 2. Resilient Rule-Based AI Engine (Offline Fallback)
        return self._generate_rule_based_advice(
            customer=customer,
            category=category,
            platform=platform,
            bill_amount=bill_amount,
            best_coupon=best_coupon,
            calculation=calculation,
            runner_up=runner_up,
            runner_up_calculation=runner_up_calculation,
            total_eligible_count=total_eligible_count,
            near_misses=near_misses or [],
            fallback_offers=fallback_offers or []
        )

    def _call_gemini_explainer(
        self,
        customer: str,
        category: str,
        platform: str,
        bill_amount: float,
        best_coupon: Optional[Dict[str, Any]],
        calculation: Optional[Dict[str, Any]],
        runner_up: Optional[Dict[str, Any]],
        runner_up_calculation: Optional[Dict[str, Any]],
        total_eligible_count: int,
        near_misses: List[Dict[str, Any]],
        fallback_offers: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Query Gemini Flash models using the modern Google Gen AI Python SDK (`from google import genai`).
        Attempts models in cascade order (gemini-3.5-flash-lite -> gemini-3.8-flash -> gemini-3.1-flash-lite).
        Guaranteed not to expose or log the API key.
        """
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)

            # Build grounded, strict prompt based on the coupon engine's verified truth
            system_instruction = (
                "You are the Smart Coupon AI shopping assistant. "
                "The backend coupon engine is the absolute source of truth for all calculations and coupon rules. "
                "CRITICAL INSTRUCTIONS:\n"
                "1. NEVER invent or hallucinate coupon codes, discounts, or terms.\n"
                "2. ONLY reference the verified coupon code and calculated discount provided in the user prompt.\n"
                "3. If no coupon is eligible, warmly explain the provided fallback offers or near-miss cart tips.\n"
                "4. Deliver an engaging, friendly, and persuasive shopping breakdown.\n"
                "5. Return your response strictly as valid JSON matching the requested schema."
            )

            if best_coupon and calculation:
                # Scenario A: Valid coupon found
                code = best_coupon.get("code")
                pct = calculation.get("discount_percentage", 0)
                actual_discount = float(calculation.get("actual_discount") or 0.0)
                raw_discount = float(calculation.get("raw_discount") or actual_discount)
                max_discount = float(calculation.get("max_discount") or 0.0)
                is_capped = calculation.get("is_capped", False)
                final_bill = float(calculation.get("final_bill") if calculation.get("final_bill") is not None else max(0.0, bill_amount - actual_discount))
                effective_pct = float(calculation.get("effective_savings_percentage") or 0.0)

                prompt_data = {
                    "task": "Explain why the recommended coupon is the best choice",
                    "customer_name": customer,
                    "shopping_category": category,
                    "shopping_platform": platform,
                    "original_bill_amount": f"₹{bill_amount:,.2f}",
                    "recommended_coupon": {
                        "code": code,
                        "description": best_coupon.get("description", ""),
                        "discount_percentage": f"{pct}%",
                        "max_discount_limit": f"₹{max_discount:,.2f}",
                        "actual_cash_discount": f"₹{actual_discount:,.2f}",
                        "final_payable_bill": f"₹{final_bill:,.2f}",
                        "effective_savings_percentage": f"{effective_pct}%",
                        "was_capped_at_maximum": is_capped
                    },
                    "total_eligible_coupons_evaluated": total_eligible_count
                }

                if runner_up and runner_up_calculation:
                    r_actual = float(runner_up_calculation.get("actual_discount") or 0.0)
                    prompt_data["runner_up_coupon"] = {
                        "code": runner_up.get("code"),
                        "discount": f"₹{r_actual:,.2f}",
                        "savings_difference": f"₹{round(actual_discount - r_actual, 2):,.2f}"
                    }

                if near_misses:
                    prompt_data["optional_cart_upgrade_tip"] = near_misses[0].get("tip", "")

            else:
                # Scenario B: No coupon eligible -> explain fallback offers
                top_fallbacks = []
                for fb in fallback_offers[:3]:
                    off = fb.get("offer", {})
                    top_fallbacks.append({
                        "title": off.get("title"),
                        "payment_method": off.get("payment_method"),
                        "benefit": off.get("benefit_summary"),
                        "is_qualified": fb.get("is_qualified", False),
                        "estimated_savings": f"₹{fb.get('estimated_savings', 0):,.2f}"
                    })

                prompt_data = {
                    "task": "Explain available fallback payment offers because no coupon code qualified",
                    "customer_name": customer,
                    "shopping_category": category,
                    "shopping_platform": platform,
                    "original_bill_amount": f"₹{bill_amount:,.2f}",
                    "reason_no_coupon": "Cart amount or category did not satisfy active coupon criteria.",
                    "available_fallback_offers": top_fallbacks,
                    "near_miss_tips": [nm.get("tip") for nm in near_misses[:2]] if near_misses else []
                }

            user_prompt = (
                f"{json.dumps(prompt_data, indent=2)}\n\n"
                "Return a JSON object with these exact keys:\n"
                "- headline (string): An eye-catching, encouraging headline\n"
                "- ai_rationale (string): Friendly 2-3 sentence personalized explanation\n"
                "- bullet_points (array of strings): 2 to 4 punchy key takeaway bullets\n"
                "- strategy_tip (string): A short checkout action tip"
            )

            # Try models in cascade
            for model_candidate in self.models_to_try:
                print(f"[Gemini AI] Querying model: '{model_candidate}'...", flush=True)
                try:
                    response = client.models.generate_content(
                        model=model_candidate,
                        contents=user_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            response_mime_type="application/json",
                            temperature=0.3
                        )
                    )

                    if response and response.text:
                        parsed = json.loads(response.text.strip())
                        if isinstance(parsed, dict) and "ai_rationale" in parsed:
                            print(f"[Gemini AI] Successfully generated advice using '{model_candidate}'.", flush=True)
                            self._last_used_model = model_candidate
                            self._last_error = None
                            parsed["engine_mode"] = f"✨ Powered by Google Gemini AI ({model_candidate})"
                            parsed["is_ai_generated"] = True
                            parsed["model_used"] = model_candidate
                            return parsed

                except Exception as model_err:
                    err_clean = self._sanitize(str(model_err))
                    err_snippet = err_clean.replace("\n", " ")[:120]
                    print(f"[Gemini AI] Model '{model_candidate}' failed ({type(model_err).__name__}: {err_snippet}). Trying next model...", flush=True)
                    self._last_error = f"{type(model_err).__name__}: {err_clean}"

            print("[Gemini AI] All models in cascade failed. Falling back to Offline Smart Rule Engine.", flush=True)

        except Exception as e:
            err_msg = self._sanitize(str(e))
            print(f"[Gemini AI] Client initialization error ({type(e).__name__}). Falling back to Offline Rule Engine.", flush=True)
            self._last_error = err_msg

        return None

    def _generate_rule_based_advice(
        self,
        customer: str,
        category: str,
        platform: str,
        bill_amount: float,
        best_coupon: Optional[Dict[str, Any]],
        calculation: Optional[Dict[str, Any]],
        runner_up: Optional[Dict[str, Any]],
        runner_up_calculation: Optional[Dict[str, Any]],
        total_eligible_count: int,
        near_misses: List[Dict[str, Any]],
        fallback_offers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        High-precision rule-based savings explanation engine.
        Runs 100% offline without any API key or network dependency.
        """
        if not best_coupon or not calculation:
            # Scenario: No coupon eligible
            points = [
                f"No standard promo code currently meets the minimum spend or category for your cart of ₹{bill_amount:,.2f}."
            ]

            # Detail fallback offers
            qualified_fallbacks = [fb for fb in fallback_offers if fb.get("is_qualified")]
            if qualified_fallbacks:
                best_fb = qualified_fallbacks[0]["offer"]
                est_save = qualified_fallbacks[0].get("estimated_savings", 0)
                points.append(
                    f"💳 **Available Payment Offer:** Use {best_fb.get('payment_method')} to save **₹{est_save:,.2f}** ({best_fb.get('title')})."
                )

            # Detail near miss tips
            if near_misses:
                top_miss = near_misses[0]
                points.append(
                    f"💡 **Cart Booster Tip:** Adding items worth **₹{top_miss['shortfall']:,.2f}** unlocks **{top_miss['coupon']['code']}** to save up to **₹{top_miss['potential_discount']:,.2f}**!"
                )

            return {
                "headline": f"Alternative Savings Plan for {customer}",
                "ai_rationale": (
                    f"Hi {customer}, we couldn't find an active coupon that unlocked at ₹{bill_amount:,.2f} "
                    f"for {category} on {platform}. However, you don't have to pay full price! "
                    f"We evaluated payment gateway offers and cart boosters below."
                ),
                "bullet_points": points,
                "strategy_tip": "Check the 'Alternative Offers' tab or add a qualifying item to unlock instant coupon discounts.",
                "engine_mode": "Offline Smart Rule Engine (Fallback Active)" if self._last_error else "Offline Smart Rule Engine",
                "is_ai_generated": False,
                "model_used": None,
                "fallback_reason": self._last_error
            }

        code = best_coupon.get("code", "PROMO")
        pct = calculation.get("discount_percentage", 0)
        actual_discount = float(calculation.get("actual_discount") or 0.0)
        raw_discount = float(calculation.get("raw_discount") or actual_discount)
        max_discount = float(calculation.get("max_discount") or 0.0)
        is_capped = calculation.get("is_capped", False)
        final_bill = float(calculation.get("final_bill") if calculation.get("final_bill") is not None else max(0.0, bill_amount - actual_discount))
        effective_pct = float(calculation.get("effective_savings_percentage") or (round((actual_discount / bill_amount) * 100.0, 1) if bill_amount > 0 else 0.0))

        points = []
        if is_capped:
            points.append(
                f"**Maximum Cap Reached:** At {pct}%, your calculated discount was ₹{raw_discount:,.2f}, capped at the maximum allowed benefit of **₹{actual_discount:,.2f}**."
            )
        else:
            points.append(
                f"**Full Percentage Benefit:** You receive the full {pct}% discount of **₹{actual_discount:,.2f}** without hitting any cap limits."
            )

        if runner_up and runner_up_calculation:
            r_actual = float(runner_up_calculation.get("actual_discount") or 0.0)
            diff = round(actual_discount - r_actual, 2)
            runner_code = runner_up.get("code", "alternative coupon")
            if diff > 0:
                points.append(
                    f"**Outperforms Competition:** Saves **₹{diff:,.2f} more** than runner-up coupon (**{runner_code}**)."
                )
            else:
                points.append(
                    f"**Tied for Top Savings:** Matches **{runner_code}** in discount value, selected for optimal validity terms."
                )
        elif total_eligible_count == 1:
            points.append(
                f"**Exclusive Match:** This is the highest-value verified coupon available for your cart."
            )

        if near_misses:
            best_miss = near_misses[0]
            pot_disc = float(best_miss.get("potential_discount") or 0.0)
            s_fall = float(best_miss.get("shortfall") or 0.0)
            if pot_disc > actual_discount:
                net_gain = round(pot_disc - actual_discount - s_fall, 2)
                if net_gain > 0:
                    nm_code = best_miss.get("coupon", {}).get("code", "VIP")
                    points.append(
                        f"💡 **AI Upgrade Insight:** Adding items worth ₹{s_fall:,.2f} unlocks **{nm_code}** (saves ₹{pot_disc:,.2f}), giving a net extra gain of ₹{net_gain:,.2f}!"
                    )

        headline = f"Optimal Discount Selected: Save ₹{actual_discount:,.2f} ({effective_pct}% off)"
        rationale = (
            f"Hello {customer}! We evaluated all available promotions for your {category} purchase on {platform}. "
            f"Coupon **{code}** emerged as your best choice because it produces the lowest net payable amount of "
            f"**₹{final_bill:,.2f}**, delivering an actual cash saving of **₹{actual_discount:,.2f}**."
        )

        return {
            "headline": headline,
            "ai_rationale": rationale,
            "bullet_points": points,
            "strategy_tip": f"Apply coupon code '{code}' at checkout on {platform} before completing payment.",
            "engine_mode": "Offline Smart Rule Engine (Fallback Active)" if self._last_error else "Offline Smart Rule Engine",
            "is_ai_generated": False,
            "model_used": None,
            "fallback_reason": self._last_error
        }
