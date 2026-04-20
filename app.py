import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import time
from datetime import datetime

st.set_page_config(page_title="Options Trading System PRO")

st.title("📊 Options Trading System (Stable Data Engine)")

# ---------------- INPUT ----------------
user_input = st.text_input("Enter 2–4 tickers (comma separated):")

max_tickers = 4

st.subheader("⚙️ Controls")
min_prob = st.slider("Min Probability (%)", 50, 80, 65)
min_credit = st.slider("Min Credit ($)", 50, 200, 100)

expiry_mode = st.selectbox("Expiry", ["Weekly", "Balanced", "Monthly"])

# ---------------- TD CONFIG ----------------
TD_API_KEY = "YOUR_TD_API_KEY_HERE"  # <-- replace

# ---------------- DATA FETCH ----------------
@st.cache_data(ttl=300)
def get_stock_yf(t):
    try:
        s = yf.Ticker(t)
        h = s.history(period="1mo")
        if h.empty:
            return None, None, None
        return s, h, float(h["Close"].iloc[-1])
    except:
        return None, None, None

def get_stock_td(t):
    try:
        url = f"https://api.tdameritrade.com/v1/marketdata/{t}/quotes"
        params = {"apikey": TD_API_KEY}
        r = requests.get(url, params=params)
        data = r.json()

        price = data[t]["lastPrice"]
        return price
    except:
        return None

def get_stock(t):
    # -------- TRY YAHOO --------
    s, h, p = get_stock_yf(t)

    if s and p:
        return s, h, p, "YF"

    # -------- FALLBACK TD --------
    p_td = get_stock_td(t)

    if p_td:
        return None, None, p_td, "TD"

    return None, None, None, "FAIL"

# ---------------- EXPIRY ----------------
@st.cache_data(ttl=300)
def get_expiry(stock):
    try:
        expiries = stock.options
        today = datetime.today()
        target = 10 if expiry_mode=="Balanced" else 5 if expiry_mode=="Weekly" else 21

        best, best_diff = None, 999
        for exp in expiries:
            dte = (datetime.strptime(exp,"%Y-%m-%d") - today).days
            diff = abs(dte-target)
            if diff < best_diff:
                best_diff = diff
                best = exp
        return best
    except:
        return None

@st.cache_data(ttl=300)
def get_chain(stock, expiry):
    try:
        return stock.option_chain(expiry)
    except:
        return None

# ---------------- PRICING ----------------
def safe_price(opt, side):
    bid = opt.get("bid", 0)
    ask = opt.get("ask", 0)
    last = opt.get("lastPrice", 0)

    if bid > 0 and ask > 0:
        return bid if side=="sell" else ask

    return last if last > 0 else 0

# ---------------- BUILD ----------------
def build_trade(stock, ticker, price, hist):

    if stock is None:
        return None  # TD fallback cannot fetch options yet

    expiry = get_expiry(stock)
    if not expiry:
        return None

    chain = get_chain(stock, expiry)
    if chain is None:
        return None

    calls = chain.calls.sort_values("strike")
    puts = chain.puts.sort_values("strike")

    ma20 = hist["Close"].rolling(20).mean().iloc[-1]
    bullish = price > ma20

    options = puts[puts["strike"] < price] if bullish else calls[calls["strike"] > price]

    best = None

    for i in range(len(options)-3):
        sell, buy = options.iloc[i], options.iloc[i+2]

        sell_price = safe_price(sell, "sell")
        buy_price = safe_price(buy, "buy")

        credit = sell_price - buy_price
        width = abs(sell["strike"] - buy["strike"])
        risk = width*100 - credit*100

        if credit <= 0 or risk <= 0:
            continue

        prob = 70
        ror = (credit*100)/risk
        dist = abs(sell["strike"] - price)/price*100

        score = prob*0.4 + ror*100*0.3 + dist*0.3

        if not best or score > best["score"]:
            best = {
                "sell": sell["strike"],
                "buy": buy["strike"],
                "credit": credit,
                "risk": risk,
                "dist": dist,
                "score": score
            }

    if not best:
        return None

    return {
        "Ticker": ticker,
        "Sell": best["sell"],
        "Buy": best["buy"],
        "Credit": round(best["credit"]*100,2),
        "Risk": round(best["risk"],2),
        "Safety Cushion": f"{round(best['dist'],2)}%",
        "Score": round(best["score"],1)
    }

# ---------------- MAIN ----------------
if st.button("Run Scan"):

    tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()][:max_tickers]

    results = []

    for t in tickers:
        stock, hist, price, source = get_stock(t)

        if price is None:
            st.warning(f"{t}: No data available")
            continue

        trade = build_trade(stock, t, price, hist)

        if trade:
            trade["Source"] = source
            results.append(trade)

        time.sleep(0.3)

    if results:
        df = pd.DataFrame(results).sort_values(by="Score", ascending=False)

        st.subheader("📊 Trades (Stable Mode)")
        st.dataframe(df, use_container_width=True)

    else:
        st.warning("No trades found.")
