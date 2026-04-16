import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Options Scanner")

st.title("📊 Options Trading Scanner")

user_input = st.text_input("Enter up to 10 tickers (comma separated):")

system_tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT"]

# ---------------- DATA ----------------
def get_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1mo")
        if data is None or data.empty:
            return None
        return data
    except:
        return None

# ---------------- MARKET CLASSIFICATION ----------------
def classify_market(data):
    close = data["Close"]
    ma20 = close.rolling(20).mean().iloc[-1]
    price = close.iloc[-1]

    if abs(price - ma20) / ma20 < 0.02:
        return "Rangebound"
    elif price > ma20:
        return "Bullish"
    else:
        return "Bearish"

# ---------------- TRADE GENERATION ----------------
def generate_trade(ticker, price, condition):
    
    prob = np.random.uniform(65, 75)  # placeholder
    credit = np.random.uniform(1.0, 2.0)
    risk = 500
    roc = (credit * 100) / risk

    if condition == "Rangebound":
        strategy = "Iron Condor"
    elif condition == "Bullish":
        strategy = "Bull Put Spread"
    else:
        strategy = "Bear Call Spread"

    score = 0.5 * prob + 0.3 * roc + 0.2 * (100 - abs(50 - prob))

    return {
        "Ticker": ticker,
        "Strategy": strategy,
        "Price": round(price, 2),
        "Probability": round(prob, 1),
        "Credit": round(credit, 2),
        "ROC (%)": round(roc, 1),
        "Score": round(score, 2),
        "Risk ($)": risk
    }

# ---------------- MAIN ----------------
if st.button("Run Scan"):

    if not user_input:
        st.warning("Please enter at least one ticker")
    else:
        st.write("🔄 Running scan...")

        user_tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()][:10]
        tickers = list(set(user_tickers + system_tickers))[:8]

        results = []

        for ticker in tickers:
            st.write(f"Checking {ticker}...")

            data = get_data(ticker)

            if data is None:
                continue

            price = float(data["Close"].iloc[-1])
            condition = classify_market(data)

            trade = generate_trade(ticker, price, condition)
            trade["Market"] = condition

            results.append(trade)

        if results:
            df = pd.DataFrame(results)

            df = df.sort_values(by=["Score", "Probability"], ascending=False).head(5)

            st.subheader("🏆 Top Trades Today")
            st.dataframe(df, use_container_width=True)
        else:
            st.error("No valid trades found.")
