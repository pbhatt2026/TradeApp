import pandas as pd
import os

FILE = "trades.csv"

def load_trades():
    if os.path.exists(FILE):
        return pd.read_csv(FILE)
    return pd.DataFrame()

def save_trades(df):
    df.to_csv(FILE, index=False)

def add_trade(trade):
    df = load_trades()
    df = pd.concat([df, pd.DataFrame([trade])], ignore_index=True)
    save_trades(df)
