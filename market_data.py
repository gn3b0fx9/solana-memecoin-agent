import os
import time
import base64
import struct
import requests
from typing import Any


DEX = "https://api.dexscreener.com"
HELIUS = "https://mainnet.helius-rpc.com/"

SESSION = requests.Session()

_PROFILE_CACHE = {
    "ts": 0.0,
    "data": [],
}

LAST_MARKET_STATUS = {
    "ok": True,
    "stage": "not_scanned",
    "error": None,
}


def market_status():
    return LAST_MARKET_STATUS.copy()


def _get(url: str, retries: int = 3, **kwargs):

    for attempt in range(retries + 1):

        r = SESSION.get(
            url,
            timeout=15,
            **kwargs,
        )

        if r.status_code == 429:

            if attempt == retries:
                r.raise_for_status()

            retry_after = r.headers.get(
                "Retry-After"
            )

            try:
                delay = (
                    float(retry_after)
                    if retry_after
                    else 2 ** (attempt + 1)
                )
            except ValueError:
                delay = 2 ** (attempt + 1)

            delay = min(
                max(delay, 2),
                30,
            )

            time.sleep(delay)

            continue

        r.raise_for_status()

        return r.json()

    raise RuntimeError(
        "HTTP request failed"
    )


def latest_solana_profiles(
    limit=20,
) -> list[dict[str, Any]]:

    now = time.time()

    if (
        _PROFILE_CACHE["data"]
        and now - _PROFILE_CACHE["ts"] < 60
    ):
        return _PROFILE_CACHE["data"][:limit]

    try:

        data = _get(
            f"{DEX}/token-profiles/latest/v1",
            retries=2,
        )

    except requests.RequestException as e:

        LAST_MARKET_STATUS.update({
            "ok": False,
            "stage": "profiles",
            "error": str(e),
        })

        return _PROFILE_CACHE["data"][:limit]

    out = []

    for x in (
        data
        if isinstance(data, list)
        else []
    ):

        if (
            x.get("chainId") == "solana"
            and x.get("tokenAddress")
        ):
            out.append(x)

        if len(out) >= limit:
            break

    _PROFILE_CACHE["ts"] = now
    _PROFILE_CACHE["data"] = out

    LAST_MARKET_STATUS.update({
        "ok": True,
        "stage": "profiles_ok",
        "error": None,
    })

    return out


def token_pairs_batch(
    mints: list[str],
) -> list[dict[str, Any]]:

    if not mints:
        return []

    url = (
        f"{DEX}/tokens/v1/solana/"
        f"{','.join(mints)}"
    )

    try:

        data = _get(
            url,
            retries=2,
        )

    except requests.RequestException as e:

        LAST_MARKET_STATUS.update({
            "ok": False,
            "stage": "token_pairs",
            "error": str(e),
        })

        return []

    return [
        p
        for p in data
        if p.get("chainId") == "solana"
    ]


def build_candidates(limit=20):

    profiles = latest_solana_profiles(
        limit
    )

    if not profiles:
        return []

    mints = [
        p["tokenAddress"]
        for p in profiles
        if p.get("tokenAddress")
    ]

    all_pairs = []

    for i in range(
        0,
        len(mints),
        30,
    ):

        batch = mints[
            i:i + 30
        ]

        all_pairs.extend(
            token_pairs_batch(batch)
        )

    pairs_by_mint = {}

    for p in all_pairs:

        base = p.get(
            "baseToken"
        ) or {}

        mint = base.get(
            "address"
        )

        if not mint:
            continue

        pairs_by_mint.setdefault(
            mint,
            [],
        ).append(p)

    candidates = []

    for profile in profiles:

        mint = profile[
            "tokenAddress"
        ]

        pairs = pairs_by_mint.get(
            mint,
            [],
        )

        if not pairs:
            continue

        pairs.sort(
            key=lambda p: float(
                (
                    p.get(
                        "liquidity"
                    ) or {}
                ).get("usd") or 0
            ),
            reverse=True,
        )

        p = pairs[0]

        liq = float(
            (
                p.get(
                    "liquidity"
                ) or {}
            ).get("usd") or 0
        )

        vol = float(
            (
                p.get(
                    "volume"
                ) or {}
            ).get("h24") or 0
        )

        price = float(
            p.get("priceUsd") or 0
        )

        tx = p.get("txns") or {}
        h24 = tx.get("h24") or {}

        buys = int(
            h24.get("buys") or 0
        )

        sells = int(
            h24.get("sells") or 0
        )

        pc = p.get(
            "priceChange"
        ) or {}

        change = float(
            pc.get("h1") or 0
        )

        candidates.append({
            "mint": mint,
            "symbol": (
                (
                    p.get(
                        "baseToken"
                    ) or {}
                ).get("symbol")
                or profile.get(
                    "description"
                )
                or mint[:6]
            ),
            "name": (
                (
                    p.get(
                        "baseToken"
                    ) or {}
                ).get("name")
                or "Unknown"
            ),
            "price_usd": price,
            "liquidity_usd": liq,
            "volume_24h_usd": vol,
            "buys_24h": buys,
            "sells_24h": sells,
            "price_change_1h": change,
            "pair_url": p.get("url"),
            "dex": p.get("dexId"),
            "profile_url": profile.get("url"),
        })

    return candidates


def helius_mint_info(
    mint: str,
) -> dict[str, Any]:

    key = os.getenv(
        "HELIUS_API_KEY"
    )

    if not key:
        return {
            "ok": False,
            "error": "HELIUS_API_KEY missing",
        }

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getAccountInfo",
        "params": [
            mint,
            {
                "encoding": "base64"
            },
        ],
    }

    try:

        r = SESSION.post(
            f"{HELIUS}?api-key={key}",
            json=payload,
            timeout=15,
        )

        r.raise_for_status()

        result = (
            r.json()
            .get("result", {})
            .get("value")
        )

    except requests.RequestException as e:

        return {
            "ok": False,
            "error": (
                "helius_request_failed: "
                f"{e}"
            ),
        }

    if not result:

        return {
            "ok": False,
            "error": "mint account not found",
        }

    try:

        raw = base64.b64decode(
            result["data"][0]
        )

        if len(raw) < 82:

            return {
                "ok": False,
                "error": (
                    "unexpected mint layout"
                ),
            }

        mint_auth_present = (
            struct.unpack_from(
                "<I",
                raw,
                0,
            )[0]
        )

        supply = (
            struct.unpack_from(
                "<Q",
                raw,
                36,
            )[0]
        )

        decimals = raw[44]

        freeze_present = (
            struct.unpack_from(
                "<I",
                raw,
                46,
            )[0]
        )

        return {
            "ok": True,
            "mint_authority_present": bool(
                mint_auth_present
            ),
            "freeze_authority_present": bool(
                freeze_present
            ),
            "supply": supply,
            "decimals": decimals,
        }

    except Exception as e:

        return {
            "ok": False,
            "error": (
                "mint_decode_failed: "
                f"{e}"
            ),
        }