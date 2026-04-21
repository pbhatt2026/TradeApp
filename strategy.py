from utils import safe_price

def build_trade(ticker, hist, price, calls, puts):

    if hist is None:
        return None

    ma20 = hist["Close"].rolling(20).mean().iloc[-1]
    bullish = price > ma20

    options = puts if bullish else calls
    options = options.sort_values("strike")

    best = None

    for i in range(len(options)-3):
        sell, buy = options.iloc[i], options.iloc[i+2]

        sell_p = safe_price(sell,"sell")
        buy_p = safe_price(buy,"buy")

        credit = sell_p - buy_p
        width = abs(sell["strike"]-buy["strike"])
        risk = width*100 - credit*100

        if credit <= 0 or risk <= 0:
            continue

        cushion = abs(sell["strike"]-price)/price*100
        score = 70 + cushion   # simple

        if not best or score > best["score"]:
            best = {
                "Sell": sell["strike"],
                "Buy": buy["strike"],
                "Credit": round(credit*100,2),
                "Risk": round(risk,2),
                "Cushion": cushion,
                "Score": score
            }

    return best
