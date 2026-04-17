import streamlit as st
import yfinance as yf
import pandas as pd
import math
from datetime import datetime

st.set_page_config(page_title="Options Trading System")

st.title("📊 Options Trading System (Execution Ready)")

# ---------------- INPUT ----------------
user_input = st.text_input("Enter up to 10 tickers (comma separated):")

max_tickers = st.slider("Max tickers to scan", 4, 15, 8)

st.subheader("⚙️ Strategy Controls")

min_prob = st.slider("Min Probability (%)", 50, 80, 65)
min_credit = st.slider("Min Credit ($)", 50, 200, 100)
min_vol = st.slider("Min Volatility (%)", 0.5, 2.0, 0.8) / 100
max_risk = st.slider("Max Risk per Trade ($)", 100, 1000, 500)

expiry_mode = st.selectbox(
    "Expiry",
    ["Weekly (0-7 DTE)", "Balanced (7-14 DTE)", "Monthly (14-30 DTE)"]
)

system_tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT"]

# ---------------- HELPERS ----------------
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

def select_expiry(stock):
    expiries = stock.options
    today = datetime.today()

    target = 10 if "Balanced" in expiry_mode else 5 if "Weekly" in expiry_mode else 21

    best = None
    diff_min = 999

    for exp in expiries:
        dte = (datetime.strptime(exp, "%Y-%m-%d") - today).days
        diff = abs(dte - target)
        if diff < diff_min:
            diff_min = diff
            best = exp

    return best

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

def get_volatility(hist):
    return hist["Close"].pct_change().abs().mean()

def estimate_probability(delta):
    return 65 if delta is None else round((1 - abs(delta)) * 100, 1)

# ---------------- LIQUIDITY ----------------
def liquidity_ok(option):
    try:
        bid = option.get("bid", 0)
        ask = option.get("ask", 0)
        volume = option.get("volume", 0)
        oi = option.get("openInterest", 0)

        if bid == 0 or ask == 0:
            return False

        spread = (ask - bid) / ((ask + bid) / 2)

        return spread < 0.15 and (volume > 50 or oi > 500)
    except:
        return False

def mid_price(option):
    bid = option.get("bid", 0)
    ask = option.get("ask", 0)
    return (bid + ask) / 2 if bid and ask else option.get("lastPrice", 0)

# ---------------- OPTIMIZER ----------------
def find_best_spread(options):

    candidates = []

    for i in range(len(options) - 3):
        sell = options.iloc[i]
        buy = options.iloc[i + 2]

        if not liquidity_ok(sell) or not liquidity_ok(buy):
            continue

        credit = mid_price(sell) - mid_price(buy)
        width = abs(sell["strike"] - buy["strike"])
        risk = width * 100 - credit * 100

        if credit <= 0 or risk <= 0 or risk > max_risk:
            continue

        delta = sell.get("delta", None)
        prob = estimate_probability(delta)
        ror = (credit * 100) / risk

        score = prob * 0.5 + ror * 100 * 0.3 + 20  # liquidity bonus baked in

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
        expiry = select_expiry(stock)
        if not expiry:
            return None

        chain = stock.option_chain(expiry)
        calls = chain.calls.sort_values("strike")
        puts = chain.puts.sort_values("strike")

        vol = get_volatility(hist)

        if condition == "Bullish":
            options = puts[puts["strike"] < price]
            best = find_best_spread(options)
            strategy = "Bull Put Spread"

        elif condition == "Bearish":
            options = calls[calls["strike"] > price]
            best = find_best_spread(options)
            strategy = "Bear Call Spread"

        else:
            return None

        if not best:
            return None

        credit = best["credit"]
        risk = best["risk"]
        prob = best["prob"]
        ror = best["ror"]

        # -------- FINAL DECISION --------
        if prob >= min_prob and credit * 100 >= min_credit and vol >= min_vol:
            decision = "🟢 TRADE"
        elif prob >= min_prob - 5:
            decision = "🟡 WATCH"
        else:
            decision = "🔴 SKIP"

        contracts = max(1, int(max_risk // risk))

        return {
            "Ticker": ticker,
            "Expiry": expiry,
            "Strategy": strategy,
            "Sell": best["sell"]["strike"],
            "Buy": best["buy"]["strike"],
            "Credit ($)": round(credit * 100, 2),
            "Risk ($)": round(risk, 2),
            "ROR (%)": round(ror * 100, 1),
            "Contracts": contracts,
            "Prob (%)": prob,
            "Decision": decision,
            "Entry": "Wait for pullback/rally",
            "Take Profit": f"${round((credit*100)*0.5,2)}",
            "Stop Loss": f"${round((credit*100)*1.5,2)}"
        }

    except:
        return None

# ---------------- MAIN ----------------
if st.button("Run Scan"):

    user_tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()]
    tickers = list(set(user_tickers + system_tickers))[:max_tickers]

    results = []

    for ticker in tickers:
        stock, hist, price = get_stock(ticker)
        if not stock:
            continue

        condition = classify_market(hist)
        trade = build_trade(stock, ticker, price, hist, condition)

        if trade:
            results.append(trade)

    if results:
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True)

        st.subheader("🔥 Only Trade These")
        st.dataframe(df[df["Decision"] == "🟢 TRADE"], use_container_width=True)

    else:
        st.warning("No execution-quality trades found.")
