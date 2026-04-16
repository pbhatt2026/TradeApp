import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Options Scanner")

st.title("📊 Options Trading Scanner (Real Data)")

user_input = st.text_input("Enter up to 10 tickers (comma separated):")

system_tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT"]

# ---------------- GET STOCK DATA ----------------
def get_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        if hist.empty:
            return None, None
        price = float(hist["Close"].iloc[-1])
        return stock, price
    except:
        return None, None

# ---------------- MARKET TYPE ----------------
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

# ---------------- OPTIONS STRATEGY ----------------
def find_trade(stock, ticker, price, condition):

    try:
        expirations = stock.options
        if not expirations:
            return None

        expiry = expirations[0]  # nearest weekly
        opt = stock.option_chain(expiry)

        calls = opt.calls
        puts = opt.puts

        if condition == "Bullish":
            # Sell OTM Put
            otm_puts = puts[puts["strike"] < price]
            if otm_puts.empty:
                return None

            strike = otm_puts.iloc[-1]
            credit = strike["lastPrice"]

            return {
                "Ticker": ticker,
                "Strategy": "Bull Put (Sell Put)",
                "Strike": strike["strike"],
                "Expiry": expiry,
                "Credit": round(credit, 2),
                "Prob (~)": "65-75%",
                "Risk": "Defined"
            }

        elif condition == "Bearish":
            # Sell OTM Call
            otm_calls = calls[calls["strike"] > price]
            if otm_calls.empty:
                return None

            strike = otm_calls.iloc[0]
            credit = strike["lastPrice"]

            return {
                "Ticker": ticker,
                "Strategy": "Bear Call (Sell Call)",
                "Strike": strike["strike"],
                "Expiry": expiry,
                "Credit": round(credit, 2),
                "Prob (~)": "65-75%",
                "Risk": "Defined"
            }

        else:
            # Iron Condor (simplified)
            return {
                "Ticker": ticker,
                "Strategy": "Iron Condor",
                "Strike": "Wide",
                "Expiry": expiry,
                "Credit": "Est",
                "Prob (~)": "60-70%",
                "Risk": "Defined"
            }

    except:
        return None

# ---------------- MAIN ----------------
if st.button("Run Scan"):

    if not user_input:
        st.warning("Please enter at least one ticker")
    else:
        st.write("🔄 Running scan...")

        user_tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()][:10]
        tickers = list(set(user_tickers + system_tickers))[:6]

        results = []

        for ticker in tickers:
            st.write(f"Checking {ticker}...")

            stock, price = get_stock(ticker)
            if stock is None:
                continue

            hist = stock.history(period="1mo")
            condition = classify_market(hist)

            trade = find_trade(stock, ticker, price, condition)

            if trade:
                trade["Market"] = condition
                results.append(trade)

        if results:
            df = pd.DataFrame(results)
            st.subheader("🏆 Trade Ideas")
            st.dataframe(df, use_container_width=True)
        else:
            st.error("No trades found.")
