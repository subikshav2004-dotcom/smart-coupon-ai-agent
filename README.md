# 🏷️ Smart Coupon AI Agent

An AI-powered shopping assistant web application built with **Python**, **Streamlit**, and **Google Gemini AI** (`gemini-2.5-flash`) that validates, compares, and recommends the best coupon or available offer to reduce a customer's shopping bill.

---

## 🚀 Features

- **Google Gemini AI Integration**:
  - Uses the official modern **Google Gen AI Python SDK** (`from google import genai`).
  - Powered by the fast, capable **`gemini-2.5-flash`** model.
  - Generates natural, personalized shopping advice and coupon value explanations.
  - Seamlessly falls back to the high-precision **Offline Rule-Based Engine** if the API key is not configured or if network/quota issues occur.
- **Secure Key Handling**:
  - Automatically loads `GEMINI_API_KEY` from the root `.env` file via `python-dotenv`.
  - The API key is never exposed, printed, or sent to client-side logs.
- **Deterministic Math & Validation**:
  - The Python `coupon_engine.py` remains the strict mathematical source of truth.
  - Gemini only recommends coupons that have strictly passed date, category, and spend checks.
  - Never hallucinates fake discount codes or non-existent promotions.
- **Modern Shopping UI**: Intuitive, attractive interface designed with shopping-themed cards, badges, and metrics.
- **Dynamic Customer Inputs**:
  - Customer Name
  - Shopping Category (`Electronics`, `Fashion`, `Food`, `Grocery`)
  - Shopping Platform (`Amazon`, `Flipkart`, `Myntra`, `Swiggy`, `Zomato`, `Blinkit`, `General / Other`)
  - Original Bill Amount
- **Rigorous Eligibility Validation**:
  - Expiry date verification (expired coupons are strictly rejected).
  - Minimum purchase amount threshold verification with shortfall calculation.
  - Category and platform matching.
- **Cap-Aware Discount Math**: Accurately computes percentage discounts against maximum cash discount limits.
- **Intelligent Coupon Ranking**: Selects the coupon delivering the highest net cash savings.
- **Smart Fallback Offers**: Suggests bank cashbacks, UPI payment discounts, and delivery fee waivers when no coupon is valid.
- **Near-Miss Shopping Tips**: Informs shoppers if adding a few rupees to their cart unlocks a much bigger coupon discount.
- **Full Catalog Browser**: Filter and inspect all coupons in the JSON database by category or active/expired status.

---

## 📁 Project Structure

```text
smart-coupon-ai-agent/
│
├── app.py                   # Streamlit frontend user interface
├── coupon_engine.py         # Validation, discount calculation, and ranking logic
├── ai_recommender.py        # Gemini AI & Rule-based advice generator
├── test_coupon_engine.py    # Unit tests for the coupon engine
├── requirements.txt         # Project dependencies (streamlit, google-genai, python-dotenv)
├── .env                     # Local environment file for GEMINI_API_KEY (git-ignored)
├── .gitignore               # Protects .env and cache files
├── README.md                # Project documentation and guide
└── data/
    ├── coupons.json         # Coupon database with codes, caps, expiry, and categories
    └── fallback_offers.json # Alternative bank, UPI, and shipping offers
```

---

## 🛠️ Installation & Setup

### 1. Prerequisites
Make sure you have **Python 3.9+** installed on your system.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Gemini API Key
Add your Gemini API key in the root `.env` file:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```
*(If the key is empty or not provided, the application will automatically run in Offline Rule-Based Mode without crashing).*

---

## ▶️ Running the Application

To launch the web application in your browser, run:
```bash
streamlit run app.py
```

The app will start and open automatically at:
```text
http://localhost:8501
```

---

## 🧪 Running Unit & Integration Tests

To run the automated tests for coupon validation and discount caps:
```bash
python test_coupon_engine.py
```
