import streamlit as st
import yfinance as yf
import pandas as pd
import math

st.set_page_config(page_title="Options Trading System")

st.title("📊 Options Trading System (Disciplined + Transparent)")

user_input = st.text_input("Enter up to 10 tickers (comma separated):")

system_tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT"]

MAX_RISK = 500

# ---------------- DATA ----------------
def get_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")

        if hist is None or hist.empty:
            return None, None, None

        price = float(hist["Close"].iloc[-1])
        return stock, hist, price
    except:
        return None, None, None

# ---------------- MARKET ----------------
def classify_market(hist):
    try:
        close = hist["Close"]
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

# ---------------- VOLATILITY ----------------
def volatility_ok(hist):
    try:
        returns = hist["Close"].pct_change().abs()
        avg_move = returns.mean()
        return avg_move > 0.01
    except:
        return False

# ---------------- PROBABILITY ----------------
def estimate_probability(price, strike):
    distance = abs(price - strike) / price

    if distance > 0.05:
        return 75
    elif distance > 0.03:
        return 70
    elif distance > 0.02:
        return 68
    else:
        return 60

# ---------------- EARNINGS ----------------
def check_earnings(stock):
    try:
        cal = stock.calendar
        if cal is not None and not cal.empty:
            return True
        return False
    except:
        return False

# ---------------- BUILD TRADE ----------------
def build_trade(stock, ticker, price, hist, condition):

    try:
        expiry = stock.options[0]
        chain = stock.option_chain(expiry)

        calls = chain.calls.sort_values("strike")
        puts = chain.puts.sort_values("strike")

        reasons = []
        status = "✅ Valid"

        # -------- STRATEGY SELECTION --------
        if condition == "Bullish":
            otm = puts[puts["strike"] < price]
            if len(otm) < 2:
                return None

            sell = otm.iloc[-1]
            buy = otm.iloc[-2]
            strategy = "Bull Put Spread"
            entry_note = "Wait for pullback near support"

        elif condition == "Bearish":
            otm = calls[calls["strike"] > price]
            if len(otm) < 2:
                return None

            sell = otm.iloc[0]
            buy = otm.iloc[1]
            strategy = "Bear Call Spread"
            entry_note = "Wait for rally near resistance"

        else:
            return {
                "Ticker": ticker,
                "Strategy": "Iron Condor",
                "Sell": "OTM",
                "Buy": "OTM",
                "Credit ($)": "Est",
                "Risk ($)": "<500",
                "Contracts": 1,
                "Prob (%)": 65,
                "Status": "⚠️ Caution",
                "Reasons": "Rangebound setup (manual tuning needed)",
                "Entry": "Sell wide range",
                "Take Profit": "50% credit",
                "Stop Loss": "1.5x credit",
                "Exit Rule": "Close before expiry",
                "Market": condition
            }

        # -------- CALCULATIONS --------
        credit = sell["lastPrice"] - buy["lastPrice"]
        spread_width = abs(sell["strike"] - buy["strike"])
        risk = spread_width * 100 - credit * 100

        prob = estimate_probability(price, sell["strike"])

        # -------- FILTER CHECKS --------
        if prob < 68:
            reasons.append("Low Probability")
            status = "❌ Reject"

        if credit * 100 < 120:
            reasons.append("Low Credit")
            status = "❌ Reject"

        if risk > MAX_RISK:
            reasons.append("High Risk")
            status = "❌ Reject"

        if not volatility_ok(hist):
            reasons.append("Low Volatility")
            status = "❌ Reject"

        if check_earnings(stock):
            reasons.append("Earnings Risk")
            if status != "❌ Reject":
                status = "⚠️ Caution"

        # -------- POSITION SIZE --------
        contracts = max(1, int(MAX_RISK // risk)) if risk > 0 else 0

        return {
            "Ticker": ticker,
            "Strategy": strategy,
            "Sell": sell["strike"],
            "Buy": buy["strike"],
            "Expiry": expiry,
            "Credit ($)": round(credit * 100, 2),
            "Risk ($)": round(risk, 2),
            "Contracts": contracts,
            "Prob (%)": prob,
            "Status": status,
            "Reasons": ", ".join(reasons) if reasons else "Meets criteria",
            "Entry": entry_note,
            "Take Profit": f"${round((credit*100)*0.5,2)}",
            "Stop Loss": f"${round((credit*100)*1.5,2)}",
            "Exit Rule": "Close 2–3 days before expiry",
            "Market": condition
        }

    except:
        return None

# ---------------- MAIN ----------------
if st.button("Run Scan"):

    if not user_input:
        st.warning("Enter at least one ticker")
    else:
        st.write("🔄 Running scan...")

        user_tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()][:10]
        tickers = list(set(user_tickers + system_tickers))[:6]

        results = []

        for ticker in tickers:
            st.write(f"Checking {ticker}...")

            stock, hist, price = get_stock(ticker)

            if stock is None:
                continue

            condition = classify_market(hist)

            trade = build_trade(stock, ticker, price, hist, condition)

            if trade:
                results.append(trade)

        # ---------------- OUTPUT ----------------
        if results:
            df = pd.DataFrame(results)

            st.subheader("📊 All Trade Candidates")
            st.dataframe(df, use_container_width=True)

            valid = df[df["Status"] == "✅ Valid"]

            if not valid.empty:
                st.subheader("🏆 Top Valid Trades")
                st.dataframe(valid.head(3), use_container_width=True)
            else:
                st.warning("⚠️ No trades fully meet criteria today. Review rejected trades above.")
        else:
            st.error("No trades generated.")
