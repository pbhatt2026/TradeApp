import streamlit as st
import pandas as pd
import time

from data import get_stock_data, get_chain, get_expiry
from strategy import build_trade
from lifecycle import create_trade_record, evaluate_exit
from storage import add_trade, load_trades
from utils import cushion_label

st.title("📊 Trading System (Lifecycle Enabled)")

tickers = st.text_input("Enter tickers (2–4):")

if st.button("Scan Trades"):

    results = []
    tickers = [t.strip().upper() for t in tickers.split(",")][:4]

    for t in tickers:
        hist, price, src = get_stock_data(t)

        expiry = get_expiry(t)
        calls, puts = get_chain(t, expiry)

        if calls is None:
            continue

        trade = build_trade(t, hist, price, calls, puts)

        if trade:
            trade["Ticker"] = t
            trade["Expiry"] = expiry
            results.append(trade)

        time.sleep(0.3)

    if results:
        df = pd.DataFrame(results)
        df["Cushion"] = df["Cushion"].apply(cushion_label)

        st.subheader("📊 Trade Ideas")
        st.dataframe(df)

        if st.button("Add Top Trade"):
            best = df.iloc[0]
            rec = create_trade_record(best["Ticker"], best, best["Expiry"])
            add_trade(rec)
            st.success("Trade Added")

# -------- OPEN TRADES --------
st.subheader("📁 Open Trades")

trades = load_trades()

if not trades.empty:

    trades["Exit Signal"] = trades.apply(evaluate_exit, axis=1)

    st.dataframe(trades)

    total_pnl = (trades["EntryCredit"] - trades["CurrentValue"]).sum()
    st.metric("Total P&L", f"${round(total_pnl,2)}")

else:
    st.info("No trades yet")
