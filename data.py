import yfinance as yf
import requests
import streamlit as st
from config import CACHE_TTL, TD_API_KEY

@st.cache_data(ttl=CACHE_TTL)
def get_price_history(t):
    try:
        s = yf.Ticker(t)
        h = s.history(period="1mo")
        if h.empty:
            return None, None
        return h, float(h["Close"].iloc[-1])
    except:
        return None, None

def get_price_td(t):
    try:
        url = f"https://api.tdameritrade.com/v1/marketdata/{t}/quotes"
        r = requests.get(url, params={"apikey": TD_API_KEY})
        return r.json()[t]["lastPrice"]
    except:
        return None

def get_stock_data(t):
    hist, price = get_price_history(t)
    if hist is not None:
        return hist, price, "YF"

    price = get_price_td(t)
    if price:
        return None, price, "TD"

    return None, None, "FAIL"

@st.cache_data(ttl=CACHE_TTL)
def get_chain(ticker, expiry):
    try:
        s = yf.Ticker(ticker)
        chain = s.option_chain(expiry)
        return chain.calls, chain.puts
    except:
        return None, None

@st.cache_data(ttl=CACHE_TTL)
def get_expiry(ticker):
    try:
        return yf.Ticker(ticker).options[0]
    except:
        return None
