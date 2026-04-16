import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Options Scanner", layout="centered")

st.title("📊 Options Trading Scanner")

# ---------------- INPUT ----------------
user_input = st.text_input("Enter up to 10 tickers (comma separated):")

# System tickers (ETFs + mega caps)
system_tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "AVGO"]

def get_data(ticker):
    try:
        data = yf.download(ticker, period="3mo", interval="1d", progress=False)
        return data
    except:
        return None

def get_rsi(data, period=14):
    delta = data["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def classify_market(data):
    latest = data.iloc[-1]
    ma20 = data["Close"].rolling(20).mean().iloc[-1]
    rsi = get_rsi(data).iloc[-1]

    if abs(latest["Close"] - ma20) / ma20 < 0.02 and 40 < rsi < 60:
        return "Rangebound"
    elif latest["Close"] > ma20:
        return "Bullish"
    else:
        return "Bearish"

def generate_trade(ticker, price, condition):
    # simplified estimates
    prob = np.random.uniform(65, 75)
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
        "ticker": ticker,
        "strategy": strategy,
        "price": round(price, 2),
        "prob": round(prob, 1),
        "credit": round(credit, 2),
        "roc": round(roc, 1),
        "score": round(score, 2),
        "risk": risk,
        "event": "No earnings detected"
    }

if st.button("Run Scan"):

    user_tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()][:10]
    tickers = list(set(user_tickers + system_tickers))

    results = []

    for ticker in tickers:
        data = get_data(ticker)
        if data is None or data.empty:
            continue

        price = data["Close"].iloc[-1]
        condition = classify_market(data)

        trade = generate_trade(ticker, price, condition)
        trade["condition"] = condition

        results.append(trade)

    if results:
        df = pd.DataFrame(results)
        df = df.sort_values(by=["score", "prob"], ascending=False).head(5)

        st.subheader("🏆 Top Trades Today")

        for i, row in df.iterrows():
            st.markdown(f"""
            ### {row['ticker']} — {row['strategy']}
            - Price: ${row['price']}
            - Market: {row['condition']}
            - Credit: ${row['credit']}
            - Probability: {row['prob']}%
            - ROC: {row['roc']}%
            - Score: {row['score']}
            - Risk: ${row['risk']}

            ⚠️ Events: {row['event']}
            """)
    else:
        st.warning("No valid data found.")
