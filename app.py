import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Options Trading System")

st.title("📊 Options Trading System (Execution + Full Visibility)")

# ---------------- INPUT ----------------
user_input = st.text_input("Enter tickers (comma separated):")
max_tickers = st.slider("Max tickers", 4, 15, 8)

min_prob = st.slider("Min Probability (%)", 50, 80, 65)
min_credit = st.slider("Min Credit ($)", 50, 200, 100)
min_vol = st.slider("Min Volatility (%)", 0.5, 2.0, 0.8) / 100
max_risk = st.slider("Max Risk ($)", 100, 1000, 500)

expiry_mode = st.selectbox(
    "Expiry",
    ["Weekly", "Balanced", "Monthly"]
)

system_tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT"]

# ---------------- HELPERS ----------------
def get_stock(t):
    try:
        s = yf.Ticker(t)
        h = s.history(period="1mo")
        if h.empty:
            return None, None, None
        return s, h, float(h["Close"].iloc[-1])
    except:
        return None, None, None

def select_expiry(stock):
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

def prob(delta):
    return 65 if delta is None else round((1-abs(delta))*100,1)

def vol(hist):
    return hist["Close"].pct_change().abs().mean()

def liquidity(opt):
    try:
        bid, ask = opt.get("bid",0), opt.get("ask",0)
        if bid==0 or ask==0:
            return True   # fallback allow

        spread = (ask-bid)/((ask+bid)/2)
        return spread < 0.25
    except:
        return True

def mid(opt):
    bid, ask = opt.get("bid",0), opt.get("ask",0)
    return (bid+ask)/2 if bid and ask else opt.get("lastPrice",0)

# ---------------- BUILD ----------------
def build_trade(stock, ticker, price, hist):

    expiry = select_expiry(stock)
    if not expiry:
        return None

    chain = stock.option_chain(expiry)
    calls = chain.calls.sort_values("strike")
    puts = chain.puts.sort_values("strike")

    market = "Bullish" if price > hist["Close"].rolling(20).mean().iloc[-1] else "Bearish"

    options = puts[puts["strike"] < price] if market=="Bullish" else calls[calls["strike"] > price]

    best = None

    for i in range(len(options)-3):
        sell, buy = options.iloc[i], options.iloc[i+2]

        if not liquidity(sell) or not liquidity(buy):
            continue

        credit = mid(sell) - mid(buy)
        width = abs(sell["strike"] - buy["strike"])
        risk = width*100 - credit*100

        if credit<=0 or risk<=0:
            continue

        delta = sell.get("delta",None)
        p = prob(delta)
        ror = (credit*100)/risk

        score = p*0.6 + ror*100*0.4

        if not best or score > best["score"]:
            best = {
                "sell": sell,
                "buy": buy,
                "credit": credit,
                "risk": risk,
                "prob": p,
                "ror": ror,
                "score": score
            }

    if not best:
        return None

    reasons = []

    if best["prob"] < min_prob:
        reasons.append("Low Prob")

    if best["credit"]*100 < min_credit:
        reasons.append("Low Credit")

    if vol(hist) < min_vol:
        reasons.append("Low Vol")

    decision = "🟢 TRADE" if len(reasons)==0 else "🟡 WATCH" if len(reasons)<=2 else "🔴 SKIP"

    return {
        "Ticker": ticker,
        "Expiry": expiry,
        "Sell": best["sell"]["strike"],
        "Buy": best["buy"]["strike"],
        "Credit": round(best["credit"]*100,2),
        "Risk": round(best["risk"],2),
        "Prob": best["prob"],
        "ROR": round(best["ror"]*100,1),
        "Decision": decision,
        "Reasons": ", ".join(reasons) if reasons else "Good Trade"
    }

# ---------------- MAIN ----------------
if st.button("Run Scan"):

    user = [t.strip().upper() for t in user_input.split(",") if t.strip()]
    tickers = list(set(user + system_tickers))[:max_tickers]

    results = []

    for t in tickers:
        s,h,p = get_stock(t)
        if not s:
            continue

        trade = build_trade(s,t,p,h)
        if trade:
            results.append(trade)

    if results:
        df = pd.DataFrame(results)

        st.subheader("📊 All Evaluated Trades")
        st.dataframe(df, use_container_width=True)

        st.subheader("🟢 Executable Trades")
        st.dataframe(df[df["Decision"]=="🟢 TRADE"], use_container_width=True)

    else:
        st.warning("No trades evaluated.")
