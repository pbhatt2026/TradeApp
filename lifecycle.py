from datetime import datetime
from config import TAKE_PROFIT, STOP_LOSS, EXIT_DTE

def create_trade_record(ticker, trade, expiry):
    return {
        "Ticker": ticker,
        "Sell": trade["Sell"],
        "Buy": trade["Buy"],
        "EntryCredit": trade["Credit"],
        "CurrentValue": trade["Credit"],
        "Expiry": expiry,
        "EntryDate": datetime.today().strftime("%Y-%m-%d"),
        "Status": "OPEN"
    }

def evaluate_exit(trade):
    credit = trade["EntryCredit"]
    current = trade["CurrentValue"]

    pnl = credit - current

    if current <= credit * (1-TAKE_PROFIT):
        return "TAKE PROFIT"

    if current >= credit * STOP_LOSS:
        return "STOP LOSS"

    return "HOLD"
