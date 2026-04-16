import streamlit as st
import yfinance as yf
import pandas as pd
import math

st.set_page_config(page_title="Options Trading System")

st.title("📊 Options Trading System (Adaptive + Real Trading Mode)")

# ---------------- INPUT ----------------
user_input = st.text_input("Enter up to 10 tickers (comma separated):")

max_tickers = st.slider("Max tickers to scan", 4, 15, 8)

# -------- TRADING CONTROLS --------
st.subheader("⚙️ Strategy Controls")

min_prob = st.slider("Min Probability (%)", 50, 80, 65)
min_credit = st.slider("Min Credit ($)", 50, 200, 100)
min_vol = st.slider("Min Volatility (daily move %)", 0.5, 2.0, 0.8) / 100
max_risk = st.slider("Max Risk per Trade ($)", 100, 1000, 500)

system_tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT"]

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
def get_volatility(hist):
    returns = hist["Close"].pct_change().abs()
    return returns.mean()

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
def find_best_spread(options):

    candidates = []

    for i in range(len(options) - 3):
        sell = options.iloc[i]
        buy = options.iloc[i + 2]

        credit = sell["lastPrice"] - buy["lastPrice"]
        width = abs(sell["strike"] - buy["strike"])
        risk = width * 100 - credit * 100

        if credit <= 0 or risk <= 0 or risk > max_risk:
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

        vol = get_volatility(hist)

        if condition == "Bullish":
            options = puts[puts["strike"] < price]
            best = find_best_spread(options)
            strategy = "Bull Put Spread"
            entry = "Wait for pullback"

        elif condition == "Bearish":
            options = calls[calls["strike"] > price]
            best = find_best_spread(options)
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

        # -------- ADAPTIVE FILTERS --------
        if prob < min_prob:
            reasons.append("Low Probability")
            status = "⚠️ Caution"

        if credit * 100 < min_credit:
            reasons.append("Low Credit")
            status = "⚠️ Caution"

        if vol < min_vol:
            reasons.append("Low Volatility")
            status = "⚠️ Caution"

        if check_earnings(stock):
            reasons.append("Earnings Risk")
            status = "⚠️ Caution"

        # Hard reject only for bad risk
        if risk > max_risk:
            status = "❌ Reject"
            reasons.append("Too Risky")

        contracts = max(1, int(max_risk // risk)) if risk > 0 else 0

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
            "Volatility (%)": round(vol * 100, 2),
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
    tickers = list(set(user_tickers + system_tickers))[:max_tickers]

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

        st.subheader("📊 Trade Candidates (Adaptive System)")
        st.dataframe(df.drop(columns=["Rank"]), use_container_width=True)

        # Summary
        st.write(
            f"✅ Valid: {len(df[df['Status']=='✅ Valid'])} | "
            f"⚠️ Caution: {len(df[df['Status']=='⚠️ Caution'])} | "
            f"❌ Reject: {len(df[df['Status']=='❌ Reject'])}"
        )

    else:
        st.warning("No trades generated.")
