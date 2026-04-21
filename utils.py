def safe_price(opt, side):
    bid, ask = opt.get("bid",0), opt.get("ask",0)
    last = opt.get("lastPrice",0)

    if bid and ask:
        return bid if side=="sell" else ask
    return last or 0

def cushion_label(v):
    if v > 4: return f"🟢 {round(v,2)}%"
    elif v > 2: return f"🟡 {round(v,2)}%"
    return f"🔴 {round(v,2)}%"
