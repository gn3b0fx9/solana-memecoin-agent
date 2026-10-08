import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from paper import run_scan, load, current_price


app = FastAPI(title="Solana Memecoin Agent — PAPER")


@app.get("/health")
def health():
    return {
        "ok": True,
        "paper_mode": os.getenv(
            "PAPER_MODE",
            "true",
        ).lower() == "true",
    }


@app.post("/api/scan")
def scan():
    try:
        return run_scan()
    except Exception as e:
        return JSONResponse(
            {
                "ok": False,
                "error": str(e),
            },
            500,
        )


@app.get("/api/state")
def state():
    return load()


@app.get("/", response_class=HTMLResponse)
def home():
    s = load()

    positions = s.get("positions", {})
    trades = s.get("trades", [])
    candidates = s.get("candidates", [])

    cash = float(s.get("cash_eur", 20))
    realized = float(
        s.get("realized_pnl_eur", 0)
    )

    position_rows = ""

    unrealized = 0.0

    for mint, p in positions.items():
        entry = float(p.get("entry_price", 0))
        quantity = float(p.get("quantity", 0))

        price = current_price(mint)

        if price:
            value = quantity * price
            pnl = value - float(
                p.get("invested_eur", 0)
            )
            unrealized += pnl
            price_text = f"${price:.8g}"
            pnl_text = f"€{pnl:+.2f}"
        else:
            value = 0
            pnl_text = "—"
            price_text = "—"

        position_rows += f"""
        <tr>
            <td>{p.get("symbol", mint[:6])}</td>
            <td>€{p.get("invested_eur", 0):.2f}</td>
            <td>${entry:.8g}</td>
            <td>{price_text}</td>
            <td>{pnl_text}</td>
        </tr>
        """

    if not position_rows:
        position_rows = """
        <tr>
            <td colspan="5">
                Nenhuma posição aberta
            </td>
        </tr>
        """

    candidate_rows = ""

    for r in candidates:
        candidate_rows += f"""
        <tr>
            <td>{r.get("symbol")}</td>
            <td>{r.get("score")}</td>
            <td>${r.get("price_usd", 0):.8g}</td>
            <td>${r.get("liquidity_usd", 0):,.0f}</td>
            <td>${r.get("volume_24h_usd", 0):,.0f}</td>
            <td>{r.get("price_change_1h", 0):.1f}%</td>
        </tr>
        """

    if not candidate_rows:
        candidate_rows = """
        <tr>
            <td colspan="6">
                Ainda sem candidatos
            </td>
        </tr>
        """

    trade_rows = ""

    for t in reversed(trades[-10:]):
        pnl = t.get("pnl_eur")

        if pnl is None:
            pnl_text = "—"
        else:
            pnl_text = f"€{float(pnl):+.2f}"

        trade_rows += f"""
        <tr>
            <td>{t.get("side")}</td>
            <td>{t.get("symbol", "—")}</td>
            <td>{pnl_text}</td>
            <td>{t.get("reason", "—")}</td>
        </tr>
        """

    if not trade_rows:
        trade_rows = """
        <tr>
            <td colspan="4">
                Ainda sem trades
            </td>
        </tr>
        """

    total_equity = cash + sum(
        float(p.get("invested_eur", 0))
        for p in positions.values()
    ) + unrealized

    return f"""
    <!doctype html>

    <html>

    <meta
        name="viewport"
        content="width=device-width,initial-scale=1"
    >

    <title>Solana Agent</title>

    <style>

    body {{
        font-family: system-ui;
        margin: 16px;
        background: #111;
        color: #eee;
    }}

    .card {{
        background: #1b1b1b;
        padding: 14px;
        border-radius: 14px;
        margin-bottom: 12px;
        overflow-x: auto;
    }}

    .safe {{
        color: #6ee7b7;
        font-weight: 700;
    }}

    .metric {{
        font-size: 22px;
        font-weight: 700;
    }}

    table {{
        width: 100%;
        font-size: 12px;
        border-collapse: collapse;
        min-width: 500px;
    }}

    td, th {{
        padding: 7px;
        border-bottom: 1px solid #333;
        text-align: left;
    }}

    </style>

    <div class="card">

        <h2>🤖 Solana Memecoin Agent</h2>

        <div class="safe">
            PAPER MODE — REAL MONEY OFF
        </div>

        <p>
            Cash:
            <span class="metric">
                €{cash:.2f}
            </span>
        </p>

        <p>
            Equity:
            <span class="metric">
                €{total_equity:.2f}
            </span>
        </p>

        <p>
            P&L realizado:
            <b>€{realized:+.2f}</b>
        </p>

        <p>
            P&L aberto:
            <b>€{unrealized:+.2f}</b>
        </p>

        <p>
            <p>
    Posições abertas:
    <b>{len(positions)}</b>
</p>

<form method="post" action="/api/scan">
    <button
        type="submit"
        style="
            padding:12px 18px;
            border:0;
            border-radius:10px;
            font-weight:700;
            font-size:16px;
        "
    >
        🔄 Scan agora
    </button>
</form>

</div>
        </p>

    </div>


    <div class="card">

        <h3>📊 Posições abertas</h3>

        <table>

            <tr>
                <th>Token</th>
                <th>Investido</th>
                <th>Entrada</th>
                <th>Atual</th>
                <th>P&L</th>
            </tr>

            {position_rows}

        </table>

    </div>


    <div class="card">

        <h3>🎯 Top candidates</h3>

        <table>

            <tr>
                <th>Token</th>
                <th>Score</th>
                <th>Price</th>
                <th>Liquidity</th>
                <th>Vol 24h</th>
                <th>1h</th>
            </tr>

            {candidate_rows}

        </table>

    </div>


    <div class="card">

        <h3>📜 Últimos trades</h3>

        <table>

            <tr>
                <th>Side</th>
                <th>Token</th>
                <th>P&L</th>
                <th>Motivo</th>
            </tr>

            {trade_rows}

        </table>

    </div>

    </html>
    """