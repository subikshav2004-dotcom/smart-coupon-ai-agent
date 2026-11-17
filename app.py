"""
Smart Coupon AI Agent - Streamlit Web Application
An AI-powered shopping assistant that validates, compares, and recommends
the optimal coupon to maximize checkout savings on any purchase.
"""

import os
import streamlit as st
from datetime import date
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Connect existing backend modules
from coupon_engine import (
    load_coupons,
    load_fallback_offers,
    find_best_coupon,
    evaluate_fallback_offers,
    calculate_discount,
    is_coupon_expired
)
from ai_recommender import AIRecommender


# ==============================================================================
# Page Configuration & Styling
# ==============================================================================
st.set_page_config(
    page_title="Smart Coupon AI Agent",
    page_icon="🏷️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern shopping-themed visual aesthetics
st.markdown("""
<style>
    /* Global styles */
    .main-header {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #db2777 100%);
        padding: 24px 28px;
        border-radius: 16px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 8px 24px rgba(79, 70, 229, 0.2);
    }
    .main-header h1 {
        color: #ffffff !important;
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0 0 6px 0;
    }
    .main-header p {
        color: #e0e7ff;
        font-size: 1.05rem;
        margin: 0;
    }

    /* Coupon Ticket Card */
    .coupon-card {
        background: #ffffff;
        border: 2px dashed #4f46e5;
        border-radius: 14px;
        padding: 20px;
        position: relative;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        margin-bottom: 16px;
        transition: transform 0.2s ease;
    }
    .coupon-card:hover {
        transform: translateY(-2px);
    }
    .coupon-card-expired {
        border-color: #ef4444;
        background: #fef2f2;
        opacity: 0.85;
    }

    /* Hero Winner Card */
    .winner-banner {
        background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
        border: 2px solid #10b981;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 6px 18px rgba(16, 185, 129, 0.15);
    }
    .coupon-code-pill {
        display: inline-block;
        background: #1e1b4b;
        color: #fbbf24 !important;
        font-family: 'Courier New', monospace;
        font-size: 1.5rem;
        font-weight: 800;
        padding: 6px 18px;
        border-radius: 10px;
        letter-spacing: 2px;
        border: 2px dashed #fbbf24;
        margin: 8px 0;
    }

    /* Metrics summary boxes */
    .bill-stat {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    .bill-stat-title {
        color: #64748b;
        font-size: 0.85rem;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .bill-stat-val {
        font-size: 1.6rem;
        font-weight: 800;
        color: #0f172a;
        margin-top: 4px;
    }
    .savings-highlight {
        color: #10b981 !important;
    }
    .final-highlight {
        color: #4f46e5 !important;
    }

    /* AI Insight Box */
    .ai-insight-box {
        background: #f5f3ff;
        border-left: 5px solid #8b5cf6;
        padding: 16px 20px;
        border-radius: 0 12px 12px 0;
        margin: 16px 0;
    }

    /* Status Badges */
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
    }
    .badge-valid { background: #d1fae5; color: #065f46; }
    .badge-expired { background: #fee2e2; color: #991b1b; }
    .badge-ineligible { background: #fef3c7; color: #92400e; }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# Helper & Data Loading
# ==============================================================================
@st.cache_data
def get_all_coupons() -> List[Dict[str, Any]]:
    """Load coupon database from JSON file."""
    return load_coupons()

@st.cache_data
def get_all_fallback_offers() -> List[Dict[str, Any]]:
    """Load fallback promotions from JSON file."""
    return load_fallback_offers()


# Initialize databases
coupons_db = get_all_coupons()
fallback_offers_db = get_all_fallback_offers()
TODAY = date.today()


# ==============================================================================
# Sidebar: Customer Profile & Shopping Cart Inputs
# ==============================================================================
with st.sidebar:
    st.image(
        "https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?auto=format&fit=crop&w=400&q=80",
        use_container_width=True
    )
    st.header("🛒 Shopping Cart Details")
    st.caption("Enter your order parameters to find the maximum savings.")

    # 1. Customer Name
    customer_name = st.text_input(
        "Customer Name",
        value="Subiksha",
        help="Personalizes your shopping savings report."
    )

    # 2. Shopping Category
    CATEGORIES = ["Electronics", "Fashion", "Food", "Grocery"]
    category = st.selectbox(
        "Shopping Category",
        options=CATEGORIES,
        index=0,
        help="Select the product category of items in your cart."
    )

    # 3. Shopping Platform
    PLATFORMS = [
        "Amazon",
        "Flipkart",
        "Myntra",
        "Swiggy",
        "Zomato",
        "Blinkit",
        "General / Other"
    ]
    platform = st.selectbox(
        "Shopping Platform",
        options=PLATFORMS,
        index=0,
        help="Platform where you are completing your checkout."
    )

    # 4. Original Bill Amount
    bill_amount = st.number_input(
        "Original Bill Amount (₹)",
        min_value=10.0,
        max_value=200000.0,
        value=3500.0,
        step=50.0,
        help="Total checkout amount before any discounts are applied."
    )

    # Quick Amount Presets
    st.markdown("**Quick Preset Amounts:**")
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        if st.button("₹450"):
            st.session_state["preset_bill"] = 450.0
    with col_p2:
        if st.button("₹1,500"):
            st.session_state["preset_bill"] = 1500.0
    with col_p3:
        if st.button("₹6,000"):
            st.session_state["preset_bill"] = 6000.0

    if "preset_bill" in st.session_state and st.session_state["preset_bill"] != bill_amount:
        bill_amount = st.session_state["preset_bill"]

    st.divider()

    # AI Configuration & Engine Settings
    st.markdown("⚙️ **AI Engine Settings**")
    
    # Securely check GEMINI_API_KEY from .env
    env_gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    has_env_key = bool(env_gemini_key)

    if has_env_key:
        st.success("🟢 **Gemini AI Connected**\nCascade: `gemini-3.5-flash-lite` → `gemini-3.8-flash`")
        use_gemini_toggle = st.toggle("Enable Gemini Explanations", value=True)
        active_api_key = env_gemini_key
    else:
        st.info("⚪ **Offline Smart Rule Engine Active**\n`GEMINI_API_KEY` not detected in `.env`.")
        with st.expander("🔑 Add Gemini API Key (Optional)", expanded=False):
            manual_key = st.text_input(
                "Gemini API Key",
                type="password",
                placeholder="Paste AIzaSy... key",
                help="Enter your key here or save it to .env as GEMINI_API_KEY."
            ).strip()
            active_api_key = manual_key if manual_key else ""
            use_gemini_toggle = bool(active_api_key)

    # Date Simulation
    simulated_date_toggle = st.toggle("Simulate Future/Past Date", value=False)
    if simulated_date_toggle:
        eval_date = st.date_input("Evaluation Date", value=TODAY)
    else:
        eval_date = TODAY
        st.caption(f"🗓️ System Date: `{eval_date.strftime('%d %b %Y')}`")

# Initialize AI Recommender with configured key & model cascade
ai_agent = AIRecommender(
    api_key=active_api_key,
    use_gemini=use_gemini_toggle
)


# ==============================================================================
# Main Content: Header & Execution
# ==============================================================================
st.markdown("""
<div class="main-header">
    <h1>🏷️ Smart Coupon AI Agent</h1>
    <p>Maximize your shopping bill savings with intelligent coupon validation, cap-aware calculations, and automatic fallback offers.</p>
</div>
""", unsafe_allow_html=True)


# Run evaluation using coupon_engine.py
eval_result = find_best_coupon(
    coupons=coupons_db,
    category=category,
    platform=platform,
    bill_amount=bill_amount,
    customer_name=customer_name,
    current_date=eval_date
)

# Extract runner-up for comparison
eligible_list = eval_result["eligible_coupons"]
runner_up_coupon = eligible_list[1]["coupon"] if len(eligible_list) > 1 else None
runner_up_calc = eligible_list[1]["calculation"] if len(eligible_list) > 1 else None

# Pre-evaluate fallback offers so AI can reference them
evaluated_fallbacks = evaluate_fallback_offers(
    fallback_offers=fallback_offers_db,
    category=category,
    platform=platform,
    bill_amount=bill_amount
)

# Generate AI explanation using ai_recommender.py (Gemini or Rule-based)
ai_report = ai_agent.generate_recommendation_summary(
    customer_name=customer_name,
    category=category,
    platform=platform,
    bill_amount=bill_amount,
    best_coupon=eval_result["best_coupon"],
    calculation=eval_result["calculation"],
    runner_up=runner_up_coupon,
    runner_up_calculation=runner_up_calc,
    total_eligible_count=len(eligible_list),
    near_misses=eval_result.get("near_misses", []),
    fallback_offers=evaluated_fallbacks
)


# ==============================================================================
# Navigation Tabs
# ==============================================================================
tab_recommend, tab_fallbacks, tab_all_coupons, tab_how_it_works = st.tabs([
    "🎯 Best Recommendation",
    "🎁 Alternative Offers",
    "📋 Browse All Coupons",
    "ℹ️ How It Works"
])


# ------------------------------------------------------------------------------
# TAB 1: Best Recommendation
# ------------------------------------------------------------------------------
with tab_recommend:
    if eval_result["found"]:
        best = eval_result["best_coupon"]
        calc = eval_result["calculation"]

        # Results Dashboard Metrics
        st.subheader(f"📊 Checkout Savings Summary for {customer_name}")
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.markdown(f"""
            <div class="bill-stat">
                <div class="bill-stat-title">Original Bill</div>
                <div class="bill-stat-val">₹{calc['original_bill']:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
            <div class="bill-stat">
                <div class="bill-stat-title">Discount Amount</div>
                <div class="bill-stat-val savings-highlight">-₹{calc['actual_discount']:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown(f"""
            <div class="bill-stat">
                <div class="bill-stat-title">Final Bill</div>
                <div class="bill-stat-val final-highlight">₹{calc['final_bill']:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        with c4:
            st.markdown(f"""
            <div class="bill-stat">
                <div class="bill-stat-title">Effective Savings</div>
                <div class="bill-stat-val savings-highlight">{calc['effective_savings_percentage']}%</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Hero Winner Card
        st.markdown(f"""
        <div class="winner-banner">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <span class="status-badge badge-valid">🏆 Best Coupon Recommendation</span>
                    <h2 style="color: #065f46; margin: 8px 0 4px 0; font-size: 1.8rem;">
                        Save ₹{calc['actual_discount']:,.2f} with <span class="coupon-code-pill">{best['code']}</span>
                    </h2>
                    <p style="color: #047857; margin: 0; font-size: 1rem;">
                        {best.get('description', 'Instant percentage discount applied to qualifying cart.')}
                    </p>
                </div>
                <div style="text-align: right; min-width: 160px; margin-top: 10px;">
                    <span style="font-size: 2.2rem; font-weight: 800; color: #047857;">{best['discount_percentage']}% OFF</span><br>
                    <small style="color: #065f46;">Up to ₹{best['max_discount']:,.2f} max discount</small>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # AI Recommendation Reason
        engine_mode_label = ai_report.get("engine_mode", "Rule-Based Engine")
        is_ai_gen = ai_report.get("is_ai_generated", False)
        badge_style = (
            "background: #d1fae5; color: #065f46; border: 1px solid #10b981;"
            if is_ai_gen else
            "background: #fef3c7; color: #92400e; border: 1px solid #f59e0b;"
        )
        st.markdown(f"""
        <div class="ai-insight-box">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
                <h4 style="margin: 0; color: #5b21b6;">💡 AI Shopping Agent Advice</h4>
                <span style="font-size: 0.8rem; padding: 4px 12px; border-radius: 12px; font-weight: 700; {badge_style}">
                    {engine_mode_label}
                </span>
            </div>
            <p style="margin: 0 0 8px 0; color: #374151; font-size: 1rem; line-height: 1.5;">
                {ai_report.get('ai_rationale') or eval_result['recommendation_reason']}
            </p>
        </div>
        """, unsafe_allow_html=True)

        # AI Strategy & Details Breakdown
        with st.expander("🤖 View Detailed AI Agent Reasoning & Breakdown", expanded=True):
            if not is_ai_gen and ai_report.get("fallback_reason"):
                st.warning(f"⚠️ Note: Gemini API was temporarily unavailable ({ai_report['fallback_reason']}). Displaying rule-based advice.")
            st.markdown(f"**AI Headline:** {ai_report.get('headline', '')}")
            st.markdown("**Key Analysis Points:**")
            for pt in ai_report.get("bullet_points", []):
                st.markdown(f"- {pt}")
            st.info(f"**Strategy Tip:** {ai_report.get('strategy_tip', '')}")
            st.caption(f"Engine: {engine_mode_label}")

        # Comparison with other eligible coupons
        if len(eligible_list) > 1:
            st.subheader(f"⚖️ Comparison with Other Eligible Coupons ({len(eligible_list)} total)")
            comp_data = []
            for item in eligible_list:
                c = item["coupon"]
                k = item["calculation"]
                is_winner = c["code"] == best["code"]
                comp_data.append({
                    "Status": "🏆 Recommended" if is_winner else "Eligible Option",
                    "Coupon Code": c["code"],
                    "Discount %": f"{c['discount_percentage']}%",
                    "Max Cap": f"₹{c['max_discount']:,.2f}",
                    "Min Spend": f"₹{c['min_purchase']:,.2f}",
                    "Actual Savings": f"₹{k['actual_discount']:,.2f}",
                    "Final Bill": f"₹{k['final_bill']:,.2f}",
                    "Savings Rate": f"{k['effective_savings_percentage']}%"
                })
            st.dataframe(comp_data, use_container_width=True)

    else:
        # No eligible coupon found
        engine_mode_label = ai_report.get("engine_mode", "Rule-Based Engine")
        is_ai_gen = ai_report.get("is_ai_generated", False)
        badge_style = (
            "background: #d1fae5; color: #065f46; border: 1px solid #10b981;"
            if is_ai_gen else
            "background: #fef3c7; color: #92400e; border: 1px solid #f59e0b;"
        )
        st.warning(f"⚠️ No coupon is currently eligible for **{category}** on **{platform}** with a bill of **₹{bill_amount:,.2f}**.")

        # Show why coupons were ineligible and explain fallback alternatives
        st.markdown(f"""
        <div class="ai-insight-box">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
                <h4 style="margin: 0; color: #5b21b6;">🔍 AI Diagnostic & Alternative Advice</h4>
                <span style="font-size: 0.8rem; padding: 4px 12px; border-radius: 12px; font-weight: 700; {badge_style}">
                    {engine_mode_label}
                </span>
            </div>
            <p style="margin: 0 0 8px 0; color: #374151; font-size: 1rem; line-height: 1.5;">
                {ai_report.get('ai_rationale') or eval_result['recommendation_reason']}
            </p>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("🤖 View AI Recommended Action Plan", expanded=True):
            if not is_ai_gen and ai_report.get("fallback_reason"):
                st.warning(f"⚠️ Note: Gemini API was temporarily unavailable ({ai_report['fallback_reason']}). Displaying rule-based advice.")
            st.markdown(f"**AI Strategy Headline:** {ai_report.get('headline', '')}")
            st.markdown("**Key Steps to Save:**")
            for pt in ai_report.get("bullet_points", []):
                st.markdown(f"- {pt}")
            st.info(f"**Action Tip:** {ai_report.get('strategy_tip', '')}")

        # Near-Miss Offers / Cart Boosters
        near_misses = eval_result.get("near_misses", [])
        if near_misses:
            st.subheader("💡 Unlock Extra Discounts by Adding More to Cart:")
            for nm in near_misses:
                c = nm["coupon"]
                st.info(
                    f"**Add ₹{nm['shortfall']:,.2f} more items** (Reach min purchase of ₹{nm['min_purchase']:,.2f}) "
                    f"to unlock **{c['code']}** ({c['discount_percentage']}% off) and save up to **₹{nm['potential_discount']:,.2f}**!"
                )

        # Fallback offers preview
        st.subheader("🎁 Suggested Alternative Payment & Store Offers:")
        st.write("Since no promo coupon code applied directly, you can still save using these available payment offers:")


# ------------------------------------------------------------------------------
# TAB 2: Alternative Offers (Bank / UPI / Delivery)
# ------------------------------------------------------------------------------
with tab_fallbacks:
    st.subheader("💳 Alternative Payment Offers & Instant Cashbacks")
    st.caption("These offers do not require coupon codes and apply via specific payment methods or cart tiers.")

    evaluated_fallbacks = evaluate_fallback_offers(
        fallback_offers=fallback_offers_db,
        category=category,
        platform=platform,
        bill_amount=bill_amount
    )

    if evaluated_fallbacks:
        fb_cols = st.columns(2)
        for idx, item in enumerate(evaluated_fallbacks):
            offer = item["offer"]
            is_qual = item["is_qualified"]
            savings = item["estimated_savings"]

            with fb_cols[idx % 2]:
                border_color = "#10b981" if is_qual else "#cbd5e1"
                bg_color = "#f0fdf4" if is_qual else "#f8fafc"
                badge_html = (
                    '<span class="status-badge badge-valid">✅ Qualified</span>'
                    if is_qual else
                    f'<span class="status-badge badge-ineligible">⏳ Spend ₹{item.get("shortfall", 0):,.2f} more</span>'
                )

                st.markdown(f"""
                <div style="background: {bg_color}; border: 1.5px solid {border_color}; border-radius: 12px; padding: 16px; margin-bottom: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <h4 style="margin: 0; color: #0f172a;">{offer.get('title')}</h4>
                        {badge_html}
                    </div>
                    <p style="color: #475569; font-size: 0.92rem; margin: 8px 0;">{offer.get('description')}</p>
                    <div style="font-size: 0.85rem; color: #64748b;">
                        <b>Payment Method:</b> {offer.get('payment_method')}<br>
                        <b>Minimum Purchase:</b> ₹{offer.get('min_purchase', 0):,.2f}<br>
                        <b>Benefit:</b> {offer.get('benefit_summary')}
                    </div>
                    {"<div style='margin-top: 10px; font-weight: 700; color: #059669;'>Estimated Saving: ₹" + f"{savings:,.2f}</div>" if is_qual else ""}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No fallback offers available for the selected category.")


# ------------------------------------------------------------------------------
# TAB 3: Browse All Coupons
# ------------------------------------------------------------------------------
with tab_all_coupons:
    st.subheader("📋 Browse All Coupons in Database")
    st.caption("Inspect live terms, discount caps, expiry dates, and categories for all registered coupons.")

    # Catalog Filter Bar
    f_col1, f_col2, f_col3 = st.columns([2, 2, 2])
    with f_col1:
        cat_filter = st.selectbox(
            "Filter by Category",
            options=["All Categories"] + CATEGORIES,
            index=0
        )
    with f_col2:
        status_filter = st.selectbox(
            "Filter by Status",
            options=["All Statuses", "Active Coupons Only", "Expired / Demo Coupons"],
            index=0
        )
    with f_col3:
        search_kw = st.text_input("Search Coupon Code", placeholder="e.g. ELECTRO, 50, FASHION")

    # Filter coupons list
    filtered_coupons = []
    for c in coupons_db:
        # Category check
        cats = c.get("applicable_categories", [])
        if cat_filter != "All Categories" and "All" not in cats and cat_filter not in cats:
            continue

        # Expiry check
        is_exp, exp_str = is_coupon_expired(c, eval_date)
        if status_filter == "Active Coupons Only" and is_exp:
            continue
        if status_filter == "Expired / Demo Coupons" and not is_exp:
            continue

        # Keyword search
        if search_kw:
            kw = search_kw.strip().lower()
            if kw not in c.get("code", "").lower() and kw not in c.get("description", "").lower():
                continue

        filtered_coupons.append((c, is_exp, exp_str))

    st.write(f"Showing **{len(filtered_coupons)}** of {len(coupons_db)} coupons:")

    # Display grid
    grid_col1, grid_col2 = st.columns(2)
    for idx, (c, is_exp, exp_str) in enumerate(filtered_coupons):
        target_col = grid_col1 if idx % 2 == 0 else grid_col2

        card_class = "coupon-card-expired" if is_exp else ""
        badge_html = (
            '<span class="status-badge badge-expired">🔴 Expired</span>'
            if is_exp else
            '<span class="status-badge badge-valid">🟢 Active</span>'
        )

        with target_col:
            st.markdown(f"""
            <div class="coupon-card {card_class}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-family: monospace; font-size: 1.25rem; font-weight: 800; color: #312e81;">
                        {c['code']}
                    </span>
                    {badge_html}
                </div>
                <div style="margin: 8px 0; color: #1e293b; font-weight: 600;">
                    {c.get('description', '')}
                </div>
                <div style="font-size: 0.86rem; color: #475569; line-height: 1.6;">
                    • <b>Discount:</b> {c['discount_percentage']}% off (Max ₹{c['max_discount']:,.2f})<br>
                    • <b>Min Spend:</b> ₹{c['min_purchase']:,.2f}<br>
                    • <b>Categories:</b> {", ".join(c.get('applicable_categories', []))}<br>
                    • <b>Expiry Date:</b> {exp_str}
                </div>
            </div>
            """, unsafe_allow_html=True)


# ------------------------------------------------------------------------------
# TAB 4: How It Works & Logic Guide
# ------------------------------------------------------------------------------
with tab_how_it_works:
    st.subheader("🧠 How Smart Coupon AI Agent Evaluates Deals")
    st.markdown("""
    The agent executes a 4-step decision pipeline:

    1. **Strict Eligibility Filter:**
       - **Expiry Date Check:** Never recommends expired coupons. Coupons with past expiry dates are rejected immediately.
       - **Category Matching:** Checks if the coupon is valid for your selected category (or marked sitewide).
       - **Minimum Spend Validation:** Verifies if your bill reaches the minimum purchase threshold.

    2. **Accurate Discount Calculation with Cap Limits:**
       $$\\text{Theoretical Discount} = \\text{Bill Amount} \\times \\left(\\frac{\\text{Discount \\%}}{100}\\right)$$
       $$\\text{Actual Discount} = \\min(\\text{Theoretical Discount},\\ \\text{Max Discount Limit})$$
       $$\\text{Final Bill} = \\max(0,\\ \\text{Bill Amount} - \\text{Actual Discount})$$

    3. **Optimal Selection & Ranking:**
       - All eligible coupons are ranked by actual discount amount in rupees (not just percentages).
       - The coupon delivering the highest cash savings is chosen as the winner.

    4. **Smart AI Fallback & Cart Boosters:**
       - If no coupon is eligible, the agent suggests alternative bank or wallet promotions.
       - Near-miss coupons are analyzed so you know if adding a small item saves you more overall.
    """)

    st.divider()
    st.markdown("### 🔌 Google Gemini AI Integration")
    st.markdown("""
    - **SDK:** Modern Google Gen AI Python SDK (`from google import genai`).
    - **Model Cascade:** Active supported Flash cascade (`gemini-3.5-flash-lite` → `gemini-3.8-flash` → `gemini-3.1-flash-lite`) with automatic failover on high demand spikes.
    - **Security:** `GEMINI_API_KEY` is loaded securely from the `.env` file via `python-dotenv` and is never logged or exposed.
    - **Deterministic Truth:** The Python coupon engine performs all validation and math calculations. Gemini explains the reasoning and synthesizes natural language recommendations without hallucinating coupon codes.
    - **Fault Tolerant:** If the Gemini API key is missing or encounters network timeouts/rate limits, the application automatically falls back to the high-precision offline rule engine.
    """)


# ==============================================================================
# Footer
# ==============================================================================
st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align: center; color: #94a3b8; font-size: 0.85rem;'>"
    "Smart Coupon AI Agent • Built with Python & Streamlit • Cap-Aware Shopping Optimization"
    "</div>",
    unsafe_allow_html=True
)
