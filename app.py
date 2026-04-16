import streamlit as st
import yfinance as yf
import pandas as pd
import math

st.set_page_config(page_title="Options Trading System")

st.title("📊 Options Trading System (Optimized Spreads)")

user_input = st.text_input("Enter up to 10 tickers (comma separated):")

system_tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT"]

MAX_RISK = 500

# ---------------- DATA ----------------
def get_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")

        if hist.empty:
            return None, None, None

        price = float(hist["Close"].iloc[-1])
        return stock, hist, price
    except:
        return None, None, None

# ---------------- MARKET ----------------
def classify_market(hist):
    close = hist["Close"]
    ma20 = close.rolling(20).mean().iloc[-1]
    price = close.iloc[-1]

    if abs(price - ma20) / ma20 < 0.02:
        return "Rangebound"
    elif price > ma20:
        return "Bullish"
    else:
        return "Bearish"

# ---------------- VOLATILITY ----------------
def volatility_ok(hist):
    returns = hist["Close"].pct_change().abs()
    return returns.mean() > 0.01

# ---------------- PROBABILITY ----------------
def estimate_probability(delta):
    if delta is None:
        return 65
    return round((1 - abs(delta)) * 100, 1)

# ---------------- EARNINGS ----------------
def check_earnings(stock):
    try:
        cal = stock.calendar
        return cal is not None and not cal.empty
    except:
        return False

# ---------------- OPTIMIZER ----------------
def find_best_spread(options, price, option_type):

    candidates = []

    for i in range(len(options) - 3):
        sell = options.iloc[i]
        buy = options.iloc[i + 2]

        credit = sell["lastPrice"] - buy["lastPrice"]
        width = abs(sell["strike"] - buy["strike"])
        risk = width * 100 - credit * 100

        if credit <= 0 or risk <= 0 or risk > MAX_RISK:
            continue

        delta = sell.get("delta", None)
        prob = estimate_probability(delta)

        ror = (credit * 100) / risk

        score = prob * 0.6 + ror * 100 * 0.4

        candidates.append({
            "sell": sell,
            "buy": buy,
            "credit": credit,
            "risk": risk,
            "prob": prob,
            "ror": ror,
            "score": score,
            "delta": delta
        })

    if not candidates:
        return None

    return sorted(candidates, key=lambda x: x["score"], reverse=True)[0]

# ---------------- BUILD TRADE ----------------
def build_trade(stock, ticker, price, hist, condition):

    try:
        expiry = stock.options[0]
        chain = stock.option_chain(expiry)

        calls = chain.calls.sort_values("strike")
        puts = chain.puts.sort_values("strike")

        if condition == "Bullish":
            options = puts[puts["strike"] < price]
            best = find_best_spread(options, price, "put")
            strategy = "Bull Put Spread"
            entry = "Wait for pullback"

        elif condition == "Bearish":
            options = calls[calls["strike"] > price]
            best = find_best_spread(options, price, "call")
            strategy = "Bear Call Spread"
            entry = "Wait for rally"

        else:
            return None

        if best is None:
            return None

        sell = best["sell"]
        buy = best["buy"]

        credit = best["credit"]
        risk = best["risk"]
        prob = best["prob"]
        ror = best["ror"]
        delta = best["delta"]

        reasons = []
        status = "✅ Valid"

        # -------- FILTERS --------
        if prob < 68:
            reasons.append("Low Probability")
            status = "❌ Reject"

        if credit * 100 < 120:
            reasons.append("Low Credit")
            status = "❌ Reject"

        if not volatility_ok(hist):
            reasons.append("Low Volatility")
            status = "❌ Reject"

        if check_earnings(stock):
            reasons.append("Earnings Risk")
            if status != "❌ Reject":
                status = "⚠️ Caution"

        contracts = max(1, int(MAX_RISK // risk))

        return {
            "Ticker": ticker,
            "Strategy": strategy,
            "Sell": sell["strike"],
            "Buy": buy["strike"],
            "Credit ($)": round(credit * 100, 2),
            "Risk ($)": round(risk, 2),
            "ROR (%)": round(ror * 100, 1),
            "Contracts": contracts,
            "Prob (%)": prob,
            "Delta": round(delta, 2) if delta else "N/A",
            "Status": status,
            "Reasons": ", ".join(reasons) if reasons else "Meets criteria",
            "Entry": entry,
            "Take Profit": f"${round((credit*100)*0.5,2)}",
            "Stop Loss": f"${round((credit*100)*1.5,2)}",
            "Market": condition
        }

    except:
        return None

# ---------------- MAIN ----------------
if st.button("Run Scan"):

    user_tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()][:10]
    tickers = list(set(user_tickers + system_tickers))[:6]

    results = []

    for ticker in tickers:
        stock, hist, price = get_stock(ticker)

        if stock is None:
            continue

        condition = classify_market(hist)

        trade = build_trade(stock, ticker, price, hist, condition)

        if trade:
            results.append(trade)

    if results:
        df = pd.DataFrame(results)

        def rank(s):
            return 0 if s == "✅ Valid" else 1 if s == "⚠️ Caution" else 2

        df["Rank"] = df["Status"].apply(rank)

        df = df.sort_values(by=["Rank", "Prob (%)"], ascending=[True, False])

        st.subheader("📊 Optimized Trade Candidates")
        st.dataframe(df.drop(columns=["Rank"]), use_container_width=True)

    else:
        st.warning("No trades generated.")
