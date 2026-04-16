import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Options Scanner")

st.title("📊 Options Trading Scanner (Spreads + Risk Control)")

user_input = st.text_input("Enter up to 10 tickers (comma separated):")

system_tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT"]

MAX_RISK = 500  # your rule

# ---------------- STOCK ----------------
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

# ---------------- SPREAD BUILDER ----------------
def build_spread(stock, ticker, price, condition):

    try:
        expiry = stock.options[0]
        chain = stock.option_chain(expiry)

        calls = chain.calls.sort_values("strike")
        puts = chain.puts.sort_values("strike")

        width = 5  # default spread width

        if condition == "Bullish":
            otm_puts = puts[puts["strike"] < price]

            if len(otm_puts) < 2:
                return None

            sell = otm_puts.iloc[-1]
            buy = otm_puts.iloc[-2]

            credit = sell["lastPrice"] - buy["lastPrice"]
            risk = (sell["strike"] - buy["strike"]) * 100 - credit * 100

            if risk > MAX_RISK or credit <= 0:
                return None

            return {
                "Ticker": ticker,
                "Strategy": "Bull Put Spread",
                "Sell Strike": sell["strike"],
                "Buy Strike": buy["strike"],
                "Expiry": expiry,
                "Credit ($)": round(credit * 100, 2),
                "Max Risk ($)": round(risk, 2),
                "Market": condition
            }

        elif condition == "Bearish":
            otm_calls = calls[calls["strike"] > price]

            if len(otm_calls) < 2:
                return None

            sell = otm_calls.iloc[0]
            buy = otm_calls.iloc[1]

            credit = sell["lastPrice"] - buy["lastPrice"]
            risk = (buy["strike"] - sell["strike"]) * 100 - credit * 100

            if risk > MAX_RISK or credit <= 0:
                return None

            return {
                "Ticker": ticker,
                "Strategy": "Bear Call Spread",
                "Sell Strike": sell["strike"],
                "Buy Strike": buy["strike"],
                "Expiry": expiry,
                "Credit ($)": round(credit * 100, 2),
                "Max Risk ($)": round(risk, 2),
                "Market": condition
            }

        else:
            return {
                "Ticker": ticker,
                "Strategy": "Iron Condor (manual)",
                "Sell Strikes": "OTM both sides",
                "Expiry": expiry,
                "Credit ($)": "Est",
                "Max Risk ($)": "<=500",
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

            trade = build_spread(stock, ticker, price, condition)

            if trade:
                results.append(trade)

        if results:
            df = pd.DataFrame(results)
            st.subheader("🏆 Trade Ideas (Risk Controlled)")
            st.dataframe(df, use_container_width=True)
        else:
            st.error("No valid spreads found under risk limit.")
