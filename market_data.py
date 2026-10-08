import os, requests
from typing import Any

DEX = "https://api.dexscreener.com"
HELIUS = "https://mainnet.helius-rpc.com/"

def _get(url: str, **kwargs):
    r = requests.get(url, timeout=15, **kwargs)
    r.raise_for_status()
    return r.json()

def latest_solana_profiles(limit=20) -> list[dict[str, Any]]:
    data = _get(f"{DEX}/token-profiles/latest/v1")
    out=[]
    for x in data if isinstance(data, list) else []:
        if x.get("chainId") == "solana" and x.get("tokenAddress"):
            out.append(x)
        if len(out) >= limit:
            break
    return out

def token_pairs(mint: str) -> list[dict[str, Any]]:
    data = _get(f"{DEX}/latest/dex/tokens/{mint}")
    return [p for p in data.get("pairs", []) if p.get("chainId") == "solana"]

def build_candidates(limit=20):
    candidates=[]
    for profile in latest_solana_profiles(limit):
        mint=profile["tokenAddress"]
        try:
            pairs=token_pairs(mint)
        except Exception:
            continue
        if not pairs: continue
        pairs.sort(key=lambda p: float((p.get("liquidity") or {}).get("usd") or 0), reverse=True)
        p=pairs[0]
        liq=float((p.get("liquidity") or {}).get("usd") or 0)
        vol=float((p.get("volume") or {}).get("h24") or 0)
        price=float(p.get("priceUsd") or 0)
        tx=p.get("txns") or {}; h24=tx.get("h24") or {}
        buys=int(h24.get("buys") or 0); sells=int(h24.get("sells") or 0)
        pc=p.get("priceChange") or {}
        change=float(pc.get("h1") or 0)
        candidates.append({
            "mint": mint, "symbol": (p.get("baseToken") or {}).get("symbol") or profile.get("description") or mint[:6],
            "name": (p.get("baseToken") or {}).get("name") or "Unknown",
            "price_usd": price, "liquidity_usd": liq, "volume_24h_usd": vol,
            "buys_24h": buys, "sells_24h": sells, "price_change_1h": change,
            "pair_url": p.get("url"), "dex": p.get("dexId"), "profile_url": profile.get("url")
        })
    return candidates

def helius_mint_info(mint: str) -> dict[str, Any]:
    key=os.getenv("HELIUS_API_KEY")
    if not key: return {"ok":False,"error":"HELIUS_API_KEY missing"}
    payload={"jsonrpc":"2.0","id":1,"method":"getAccountInfo","params":[mint,{"encoding":"base64"}]}
    r=requests.post(f"{HELIUS}?api-key={key}",json=payload,timeout=15); r.raise_for_status()
    result=r.json().get("result",{}).get("value")
    if not result: return {"ok":False,"error":"mint account not found"}
    import base64, struct
    raw=base64.b64decode(result["data"][0])
    if len(raw)<82: return {"ok":False,"error":"unexpected mint layout"}
    mint_auth_present=struct.unpack_from("<I",raw,0)[0]
    supply=struct.unpack_from("<Q",raw,36)[0]
    decimals=raw[44]
    freeze_present=struct.unpack_from("<I",raw,46)[0]
    return {"ok":True,"mint_authority_present":bool(mint_auth_present),"freeze_authority_present":bool(freeze_present),"supply":supply,"decimals":decimals}
