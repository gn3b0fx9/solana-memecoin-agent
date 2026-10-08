import os

def env_float(k, d):
    try: return float(os.getenv(k, d))
    except: return float(d)

def score(c, mint_info):
    s=0; reasons=[]
    liq=c["liquidity_usd"]; vol=c["volume_24h_usd"]
    if liq >= env_float("MIN_LIQUIDITY_USD",25000): s+=30; reasons.append("liquidity")
    elif liq >= 10000: s+=15; reasons.append("medium liquidity")
    if vol >= env_float("MIN_VOLUME_24H_USD",15000): s+=25; reasons.append("volume")
    if c["buys_24h"] > c["sells_24h"]*1.15 and c["buys_24h"] >= 20: s+=15; reasons.append("buy pressure")
    elif c["sells_24h"] > c["buys_24h"]*1.5: s-=20; reasons.append("sell pressure")
    ch=c["price_change_1h"]
    if -20 <= ch <= 40: s+=10; reasons.append("reasonable 1h move")
    elif ch > 100: s-=15; reasons.append("vertical move")
    if mint_info.get("ok"):
        if not mint_info.get("mint_authority_present"): s+=5; reasons.append("mint authority disabled")
        else: s-=10; reasons.append("mint authority active")
        if not mint_info.get("freeze_authority_present"): s+=5; reasons.append("freeze authority disabled")
        else: s-=15; reasons.append("freeze authority active")
    return max(0,min(100,s)), reasons
