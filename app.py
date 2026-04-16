import streamlit as st

st.set_page_config(page_title="Options Scanner")

st.title("📊 Options Trading Scanner")

st.write("Enter up to 10 tickers below:")

user_input = st.text_input("Tickers (comma separated):")

if st.button("Run Scan"):
    if not user_input:
        st.warning("Please enter at least one ticker")
    else:
        tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()]
        st.success(f"Tickers received: {tickers}")
