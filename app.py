import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Options Trading System PRO")

st.title("📊 Options Trading System (Pro Execution Engine)")

# ---------------- INPUT ----------------
user_input = st.text_input("Enter tickers (comma separated):")
max_tickers = st.slider("Max tickers", 4, 15, 8)

st.subheader("⚙️ Strategy Controls")
min_prob = st.slider("Min Probability (%)", 50, 80, 65)
min_credit = st.slider("Min Credit ($)", 50, 200, 100)
min_vol = st.slider("Min Volatility (%)", 0.5, 2.0, 0.8) / 100
max_risk = st.slider("Max Risk ($)", 100, 1000, 500)

expiry_mode = st.selectbox("Expiry", ["Weekly", "Balanced", "Monthly"])

system_tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT"]

# ---------------- DATA ----------------
def get_stock(t):
    try:
        s = yf.Ticker(t)
        h = s.history(period="1mo")
        if h.empty:
            return None, None, None
        return s, h, float(h["Close"].iloc[-1])
    except:
        return None, None, None

# ---------------- EXPIRY ----------------
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

# ---------------- METRICS ----------------
def prob(delta):
    return 65 if delta is None else round((1-abs(delta))*100,1)

def vol(hist):
    return hist["Close"].pct_change().abs().mean()

def mid(opt):
    bid, ask = opt.get("bid",0), opt.get("ask",0)
    return (bid+ask)/2 if bid and ask else opt.get("lastPrice",0)

# ---------------- ENTRY ----------------
def entry_zone(hist):
    return hist["Low"].tail(5).min(), hist["High"].tail(5).max()

# ---------------- GREEKS ENGINE ----------------
def estimate_delta(strike, price):
    return min(0.5, 0.1 + abs(strike-price)/price)

def estimate_theta(dte):
    return -1/max(dte,1)

def estimate_vega(dte):
    return 0.1*(dte/30)

def estimate_gamma(strike, price):
    return max(0.01, 0.1 - abs(strike-price)/price)

def get_greeks(opt, price, dte):
    delta = opt.get("delta") or estimate_delta(opt["strike"], price)
    theta = opt.get("theta") or estimate_theta(dte)
    vega = opt.get("vega") or estimate_vega(dte)
    gamma = opt.get("gamma") or estimate_gamma(opt["strike"], price)
    return delta, theta, vega, gamma

# ---------------- BUILD ----------------
def build_trade(stock, ticker, price, hist):

    expiry = select_expiry(stock)
    if not expiry:
        return None

    exp_date = datetime.strptime(expiry,"%Y-%m-%d")
    dte = (exp_date - datetime.today()).days

    chain = stock.option_chain(expiry)
    calls = chain.calls.sort_values("strike")
    puts = chain.puts.sort_values("strike")

    ma20 = hist["Close"].rolling(20).mean().iloc[-1]
    market = "Bullish" if price > ma20 else "Bearish"

    low, high = entry_zone(hist)

    if market=="Bullish":
        options = puts[puts["strike"] < price]
        strategy = "Bull Put Spread"
        opt_type = "PUT"
        entry_text = f"Enter near ${round(low,2)}"
    else:
        options = calls[calls["strike"] > price]
        strategy = "Bear Call Spread"
        opt_type = "CALL"
        entry_text = f"Enter near ${round(high,2)}"

    best = None

    for i in range(len(options)-3):
        sell, buy = options.iloc[i], options.iloc[i+2]

        credit = mid(sell) - mid(buy)
        width = abs(sell["strike"] - buy["strike"])
        risk = width*100 - credit*100

        if credit<=0 or risk<=0:
            continue

        sd, stheta, svega, sgamma = get_greeks(sell, price, dte)
        bd, btheta, bvega, bgamma = get_greeks(buy, price, dte)

        net_theta = stheta - btheta
        net_vega = svega - bvega
        gamma = sgamma

        p = prob(sd)
        ror = (credit*100)/risk
        dist = abs(sell["strike"] - price)/price*100

        score = (
            p*0.35 +
            ror*100*0.2 +
            net_theta*100*0.2 +
            dist*0.15 -
            abs(net_vega)*0.1
        )

        if not best or score > best["score"]:
            best = {
                "sell": sell,
                "buy": buy,
                "credit": credit,
                "risk": risk,
                "prob": p,
                "ror": ror,
                "dist": dist,
                "theta": net_theta,
                "vega": net_vega,
                "gamma": gamma,
                "score": score
            }

    if not best:
        return None

    # -------- DECISION --------
    reasons = []

    if best["prob"] < min_prob:
        reasons.append("Low Prob")
    if best["credit"]*100 < min_credit:
        reasons.append("Low Credit")
    if vol(hist) < min_vol:
        reasons.append("Low Vol")
    if best["gamma"] > 0.08:
        reasons.append("High Gamma")
    if best["theta"] < 0:
        reasons.append("Low Theta")

    decision = "🟢 TRADE" if len(reasons)==0 else "🟡 WATCH" if len(reasons)<=2 else "🔴 SKIP"

    return {
        "Ticker": ticker,
        "Expiry": expiry,
        "Strategy": strategy,
        "Type": opt_type,
        "Sell": best["sell"]["strike"],
        "Buy": best["buy"]["strike"],
        "Entry Zone": entry_text,
        "Strike Dist %": round(best["dist"],2),
        "Credit": round(best["credit"]*100,2),
        "Risk": round(best["risk"],2),
        "Prob": best["prob"],
        "ROR": round(best["ror"]*100,1),
        "Theta": round(best["theta"],4),
        "Vega": round(best["vega"],4),
        "Gamma": round(best["gamma"],4),
        "Decision": decision,
        "Reasons": ", ".join(reasons) if reasons else "Strong Setup"
    }

# ---------------- COLORING ----------------
def highlight(val, col):
    try:
        val = float(val)
    except:
        return ""

    if col=="Theta":
        color = "green" if val>0.02 else "orange" if val>0 else "red"
    elif col=="Vega":
        color = "green" if abs(val)<0.05 else "orange" if abs(val)<0.15 else "red"
    elif col=="Gamma":
        color = "green" if val<0.03 else "orange" if val<0.08 else "red"
    else:
        return ""

    return f"color:{color}; font-weight:bold"

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

        st.subheader("📊 All Trades (Execution View)")

        styled = df.style \
            .applymap(lambda v: highlight(v,"Theta"), subset=["Theta"]) \
            .applymap(lambda v: highlight(v,"Vega"), subset=["Vega"]) \
            .applymap(lambda v: highlight(v,"Gamma"), subset=["Gamma"])

        st.dataframe(styled, use_container_width=True)

        st.subheader("🟢 Best Trades")
        st.dataframe(df[df["Decision"]=="🟢 TRADE"], use_container_width=True)

    else:
        st.warning("No trades evaluated.")
