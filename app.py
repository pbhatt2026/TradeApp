import streamlit as st
import yfinance as yf
import pandas as pd

# ---------------- PAGE SETUP ----------------
st.set_page_config(page_title="Options Scanner", layout="centered")

st.title("📊 Options Trading Scanner")

st.write("Enter up to 10 tickers (comma separated):")

# ---------------- INPUT ----------------
user_input = st.text_input("Tickers")

# System tickers (safe + liquid)
system_tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT"]

# ---------------- FUNCTIONS ----------------

def get_data(ticker):
    try:
        data = yf.download(
            ticker,
            period="1mo",
            interval="1d",
            progress=False,
            threads=False
        )

        if data is None or data.empty:
            st.write(f"⚠️ No data for {ticker}")
            return None

        return data

    except Exception as e:
        st.write(f"❌ Error for {ticker}: {e}")
        return None


def get_price(data):
    try:
        return float(round(data["Close"].iloc[-1], 2))
    except:
        return None


def classify_market(data):
    try:
        close = data["Close"]
        ma20 = close.rolling(20).mean().iloc[-1]
        price = close.iloc[-1]

        if pd.isna(ma20):
            return "Neutral"

        if abs(price - ma20) / ma20 < 0.02:
            return "Rangebound"
        elif price > ma20:
            return "Bullish"
        else:
            return "Bearish"
    except:
        return "Unknown"


# ---------------- MAIN ACTION ----------------

if st.button("Run Scan"):

    if not user_input:
        st.warning("Please enter at least one ticker")
    else:
        st.write("🔄 Running scan...")

        # Parse user tickers
        user_tickers = [
            t.strip().upper()
            for t in user_input.split(",")
            if t.strip()
        ][:10]

        # Combine with system tickers
        tickers = list(set(user_tickers + system_tickers))[:8]  # limit for performance

        results = []

        for ticker in tickers:
            st.write(f"Checking {ticker}...")

            data = get_data(ticker)

            if data is None:
                continue

            price = get_price(data)

            if price is None:
                continue

            condition = classify_market(data)

            results.append({
                "Ticker": ticker,
                "Price": price,
                "Market": condition
            })

        # ---------------- OUTPUT ----------------

        if results:
            df = pd.DataFrame(results)

            st.subheader("✅ Scan Results")
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("No valid data found.")
