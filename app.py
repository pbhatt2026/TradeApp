import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Options Scanner")

st.title("📊 Options Trading Scanner")

user_input = st.text_input("Enter up to 10 tickers (comma separated):")

system_tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT"]

def get_price(ticker):
    try:
        data = yf.download(ticker, period="5d", interval="1d", progress=False, threads=False)
        if data.empty:
            return None
        return round(data["Close"].iloc[-1], 2)
    except:
        return None

if st.button("Run Scan"):

    if not user_input:
        st.warning("Please enter at least one ticker")
    else:
        st.write("🔄 Running scan...")

        user_tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()][:10]
        tickers = list(set(user_tickers + system_tickers))[:8]   # limit for speed

        results = []

        for ticker in tickers:
            st.write(f"Checking {ticker}...")
            price = get_price(ticker)

            if price:
                results.append((ticker, price))

        if results:
            st.subheader("✅ Results")

            for t, p in results:
                st.write(f"{t}: ${p}")
        else:
            st.warning("No data found.")
