import json
import os
import time

from market_data import (
    build_candidates,
    helius_mint_info,
    token_pairs_batch,
)
from risk import score


STATE_FILE = "paper_state.json"


def env_float(key, default):
    try:
        return float(os.getenv(key, default))
    except Exception:
        return float(default)


def env_int(key, default):
    try:
        return int(os.getenv(key, default))
    except Exception:
        return int(default)


def default_state():
    return {
        "cash_eur": env_float("STARTING_EUR", 20),
        "positions": {},
        "trades": [],
        "last_scan": None,
        "realized_pnl_eur": 0.0,
    }


def load():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)

            state.setdefault("cash_eur", env_float("STARTING_EUR", 20))
            state.setdefault("positions", {})
            state.setdefault("trades", [])
            state.setdefault("last_scan", None)
            state.setdefault("realized_pnl_eur", 0.0)

            return state

        except Exception:
            pass

    return default_state()


def save(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def today_start():
    return int(time.time()) - 86400


def daily_realized_pnl(state):
    total = 0.0
    cutoff = today_start()

    for trade in state.get("trades", []):
        if trade.get("side") != "SELL":
            continue

        if trade.get("timestamp", 0) >= cutoff:
            total += float(trade.get("pnl_eur", 0))

    return total


def current_price(mint):
    try:
        pairs = token_pairs_batch([mint])

        if not pairs:
            return None

        pairs.sort(
            key=lambda p: float(
                (p.get("liquidity") or {}).get("usd") or 0
            ),
            reverse=True,
        )

        price = float(pairs[0].get("priceUsd") or 0)

        if price <= 0:
            return None

        return price

    except Exception:
        return None


def close_position(state, mint, price, reason):
    position = state["positions"].get(mint)

    if not position:
        return

    quantity = float(position["quantity"])
    invested = float(position["invested_eur"])

    # Small simulated execution cost.
    slippage = env_float("PAPER_SLIPPAGE", 0.005)

    proceeds = quantity * price * (1 - slippage)
    pnl = proceeds - invested

    state["cash_eur"] += proceeds
    state["realized_pnl_eur"] += pnl

    state["trades"].append({
        "timestamp": int(time.time()),
        "side": "SELL",
        "mint": mint,
        "symbol": position.get("symbol"),
        "price_usd": price,
        "quantity": quantity,
        "proceeds_eur": proceeds,
        "pnl_eur": pnl,
        "reason": reason,
    })

    del state["positions"][mint]


def manage_positions(state):
    stop_loss = env_float("PAPER_STOP_LOSS", 0.08)
    take_profit = env_float("PAPER_TAKE_PROFIT", 0.15)

    for mint in list(state["positions"].keys()):
        position = state["positions"][mint]

        price = current_price(mint)

        if price is None:
            continue

        entry_price = float(position["entry_price"])

        change = (price / entry_price) - 1

        if change <= -stop_loss:
            close_position(
                state,
                mint,
                price,
                "stop_loss",
            )

        elif change >= take_profit:
            close_position(
                state,
                mint,
                price,
                "take_profit",
            )


def open_position(state, candidate):
    max_position = env_float("MAX_POSITION_EUR", 2)
    min_cash = env_float("MIN_CASH_EUR", 8)
    max_positions = env_int("MAX_POSITIONS", 4)

    if len(state["positions"]) >= max_positions:
        return False

    if candidate["mint"] in state["positions"]:
        return False

    if state["cash_eur"] - max_position < min_cash:
        return False

    daily_loss_limit = env_float(
        "MAX_DAILY_LOSS_EUR",
        1,
    )

    if daily_realized_pnl(state) <= -daily_loss_limit:
        return False

    price = float(candidate.get("price_usd") or 0)

    if price <= 0:
        return False

    slippage = env_float("PAPER_SLIPPAGE", 0.005)

    invested = max_position

    # Simulate buying slightly above the displayed market price.
    execution_price = price * (1 + slippage)

    quantity = invested / execution_price

    state["cash_eur"] -= invested

    state["positions"][candidate["mint"]] = {
        "mint": candidate["mint"],
        "symbol": candidate.get("symbol"),
        "name": candidate.get("name"),
        "entry_price": execution_price,
        "quantity": quantity,
        "invested_eur": invested,
        "entry_timestamp": int(time.time()),
        "entry_score": candidate.get("score", 0),
    }

    state["trades"].append({
        "timestamp": int(time.time()),
        "side": "BUY",
        "mint": candidate["mint"],
        "symbol": candidate.get("symbol"),
        "price_usd": execution_price,
        "quantity": quantity,
        "invested_eur": invested,
        "score": candidate.get("score", 0),
    })

    return True


def run_scan():
    if os.getenv("PAPER_MODE", "true").lower() != "true":
        raise RuntimeError(
            "PAPER_MODE must remain true"
        )

    state = load()

    # First manage positions already open.
    manage_positions(state)

    limit = env_int("SCAN_LIMIT", 20)

    candidates = build_candidates(limit)

    ranked = []

    for candidate in candidates:
        mint_info = helius_mint_info(
            candidate["mint"]
        )

        sc, reasons = score(
            candidate,
            mint_info,
        )

        candidate.update({
            "score": sc,
            "reasons": reasons,
            "mint_checks": mint_info,
        })

        ranked.append(candidate)

    ranked.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    state["last_scan"] = int(time.time())
    state["candidates"] = ranked[:20]

    # Daily loss protection.
    daily_loss_limit = env_float(
        "MAX_DAILY_LOSS_EUR",
        1,
    )

    if daily_realized_pnl(state) > -daily_loss_limit:
        # Only one new position per scan.
        for candidate in ranked:
            if candidate["score"] < 70:
                break

            if open_position(
                state,
                candidate,
            ):
                break

    save(state)

    return state
