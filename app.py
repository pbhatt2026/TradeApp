import streamlit as st
import yfinance as yf
import pandas as pd
import math

st.set_page_config(page_title="Options Trading System")

st.title("📊 Options Trading System (Disciplined Mode)")

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

# ---------------- VOLATILITY FILTER ----------------
def volatility_ok(hist):
    returns = hist["Close"].pct_change().abs()
    avg_move = returns.mean()
    return avg_move > 0.01  # ~1% daily move

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

# ---------------- SPREAD ----------------
def build_trade(stock, ticker, price, hist, condition):

    try:
        expiry = stock.options[0]
        chain = stock.option_chain(expiry)

        calls = chain.calls.sort_values("strike")
        puts = chain.puts.sort_values("strike")

        if condition == "Bullish":
            otm = puts[puts["strike"] < price]
            if len(otm) < 2:
                return None

            sell = otm.iloc[-1]
            buy = otm.iloc[-2]

            strategy = "Bull Put Spread"
            entry_note = "Enter on pullback near support"

        else:
            otm = calls[calls["strike"] > price]
            if len(otm) < 2:
                return None

            sell = otm.iloc[0]
            buy = otm.iloc[1]

            strategy = "Bear Call Spread"
            entry_note = "Enter on rally near resistance"

        credit = sell["lastPrice"] - buy["lastPrice"]
        risk = abs(sell["strike"] - buy["strike"]) * 100 - credit * 100

        if credit <= 0 or risk > MAX_RISK:
            return None

        prob = estimate_probability(price, sell["strike"])

        # -------- STRICT FILTERS --------
        if prob < 68:
            return None

        if credit * 100 < 120:
            return None

        if not volatility_ok(hist):
            return None

        if check_earnings(stock):
            return None

        contracts = math.floor(MAX_RISK / risk)
        if contracts < 1:
            return None

        return {
            "Ticker": ticker,
            "Strategy": strategy,
            "Sell": sell["strike"],
            "Buy": buy["strike"],
            "Credit ($)": round(credit * 100, 2),
            "Risk ($)": round(risk, 2),
            "Contracts": contracts,
            "Prob (%)": prob,
            "Entry": entry_note,
            "Take Profit": f"${round((credit*100)*0.5,2)}",
            "Stop Loss": f"${round((credit*100)*1.5,2)}",
            "Exit Rule": "Close 2–3 days before expiry"
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

        st.subheader("🏆 Top Trades (Max 3)")
        st.dataframe(df.head(3), use_container_width=True)
    else:
        st.warning("No trades meet strict criteria today.")
