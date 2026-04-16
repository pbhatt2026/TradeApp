import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Options Scanner")

st.title("📊 Options Trading Scanner")

user_input = st.text_input("Enter up to 10 tickers (comma separated):")

system_tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT"]

# ---------------- SAFE DATA FETCH ----------------
def get_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="5d")

        if data is None or data.empty:
            st.write(f"⚠️ No data for {ticker}")
            return None

        price = float(data["Close"].iloc[-1])
        return round(price, 2)

    except Exception as e:
        st.write(f"❌ Error for {ticker}: {e}")
        return None

# ---------------- MAIN ----------------
if st.button("Run Scan"):

    if not user_input:
        st.warning("Please enter at least one ticker")
    else:
        st.write("🔄 Running scan...")

        user_tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()][:10]
        tickers = list(set(user_tickers + system_tickers))[:8]

        results = []

        for ticker in tickers:
            st.write(f"Checking {ticker}...")

            price = get_price(ticker)

            if price is not None:
                st.write(f"{ticker} price: ${price}")

                results.append({
                    "Ticker": ticker,
                    "Price": price
                })

        if results:
            df = pd.DataFrame(results)

            st.subheader("✅ Results")
            st.dataframe(df, use_container_width=True)
        else:
            st.error("❌ No valid data found. Try different tickers.")
