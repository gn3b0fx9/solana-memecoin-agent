import os
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Solana Memecoin Agent")

START = float(os.getenv("STARTING_EUR", "20"))
MAX_POS = float(os.getenv("MAX_POSITION_EUR", "2"))
MIN_CASH = float(os.getenv("MIN_CASH_EUR", "8"))
MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS_EUR", "1"))

state = {
    "cash": START,
    "positions": [],
    "trades": [],
    "daily_pnl": 0.0,
    "running": True,
    "mode": "PAPER",
}

# These are clearly labelled demo candidates. Replace this adapter with
# real Solana market-data APIs before using the agent for meaningful tests.
candidates = [
    {"symbol": "DEMO-A", "liquidity": 90000, "volume": 180000, "momentum": 0.12, "risk": 0.20},
    {"symbol": "DEMO-B", "liquidity": 22000, "volume": 120000, "momentum": 0.18, "risk": 0.55},
    {"symbol": "DEMO-C", "liquidity": 150000, "volume": 190000, "momentum": 0.05, "risk": 0.10},
]


def score(c):
    liquidity = min(c["liquidity"] / 100000, 1)
    volume = min(c["volume"] / max(c["liquidity"], 1) / 4, 1)
    momentum = max(0, min(c["momentum"] / 0.20, 1))
    return round(100 * (
        0.40 * liquidity +
        0.25 * volume +
        0.25 * momentum -
        0.50 * c["risk"]
    ), 1)


def candidate_view():
    out = []
    for c in candidates:
        s = score(c)
        action = "BUY (PAPER)" if state["running"] and s >= 35 and c["risk"] < 0.45 else "SKIP"
        out.append({**c, "score": s, "action": action})
    return out


@app.get("/health")
def health():
    return {"status": "ok", "mode": state["mode"]}


@app.get("/api/state")
def api_state():
    equity = state["cash"] + sum(p["eur"] for p in state["positions"])
    return {
        "equity": round(equity, 2),
        "cash": round(state["cash"], 2),
        "daily_pnl": round(state["daily_pnl"], 2),
        "running": state["running"],
        "mode": state["mode"],
        "max_position": MAX_POS,
        "min_cash": MIN_CASH,
        "candidates": candidate_view(),
        "trades": state["trades"][-20:],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/kill")
def kill():
    state["running"] = False
    return {"ok": True}


@app.post("/api/resume")
def resume():
    state["running"] = True
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """<!doctype html>
<html lang="en">
<head>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Solana Agent</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f5f5f7;color:#111;font-family:-apple-system,BlinkMacSystemFont,system-ui,sans-serif}
main{max-width:720px;margin:auto;padding:16px;padding-bottom:40px}.card{background:#fff;border-radius:18px;padding:18px;margin:12px 0;box-shadow:0 2px 12px #0000000b}
h1{font-size:24px;margin:0 0 4px}.muted{color:#6b6b70}.big{font-size:36px;font-weight:750;margin:7px 0 15px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.label{font-size:13px;color:#777}
.row{display:flex;align-items:center;justify-content:space-between;padding:12px 0;border-bottom:1px solid #eee}.row:last-child{border:0}
.badge{padding:5px 8px;border-radius:9px;background:#eee;font-size:12px}
button{padding:12px 15px;border:0;border-radius:12px;font-weight:700;margin:5px 5px 0 0}
.stop{background:#fee;color:#900}.go{background:#e9f8ee;color:#176b31}
.warning{background:#fff7df;padding:11px;border-radius:12px;font-size:13px}
</style>
</head>
<body><main>
<div class="card">
<h1>🟣 Solana Memecoin Agent</h1>
<div class="muted">€20 • PAPER TRADING • GitHub + Render</div>
</div>

<div class="card">
<div class="label">Paper equity</div><div class="big" id="equity">€20.00</div>
<div class="grid">
<div><div class="label">Cash</div><b id="cash">€20.00</b></div>
<div><div class="label">Daily P/L</div><b id="pnl">€0.00</b></div>
</div>
</div>

<div class="card">
<b>Agent status</b>
<p id="status">Loading...</p>
<button class="stop" onclick="post('/api/kill')">KILL SWITCH</button>
<button class="go" onclick="post('/api/resume')">RESUME</button>
</div>

<div class="card">
<b>Candidate scan</b>
<div class="warning">Demo data only. No real tokens are being traded.</div>
<div id="candidates">Loading...</div>
</div>

<div class="card">
<b>Risk rules</b>
<p class="muted">Max position €2 · minimum cash €8 · daily loss limit €1 · max 4 positions · no leverage.</p>
</div>

<div class="card">
<b>Recent paper trades</b>
<div id="trades">None</div>
</div>

<script>
async function post(url){await fetch(url,{method:'POST'});refresh()}
async function refresh(){
 const s=await (await fetch('/api/state')).json();
 document.querySelector('#equity').textContent='€'+s.equity.toFixed(2);
 document.querySelector('#cash').textContent='€'+s.cash.toFixed(2);
 document.querySelector('#pnl').textContent='€'+s.daily_pnl.toFixed(2);
 document.querySelector('#status').textContent=s.running?'🟢 Running — '+s.mode:'🔴 STOPPED — '+s.mode;
 document.querySelector('#candidates').innerHTML=s.candidates.map(c =>
 `<div class="row"><span><b>${c.symbol}</b><br><span class="muted">score ${c.score} · risk ${c.risk}</span></span><span class="badge">${c.action}</span></div>`
 ).join('');
 document.querySelector('#trades').innerHTML=s.trades.length
 ? s.trades.slice().reverse().map(t=>`<div class="row"><span>${t.action} ${t.symbol}</span><span>€${Number(t.eur).toFixed(2)}</span></div>`).join('')
 : '<span class="muted">No trades yet.</span>';
}
refresh();setInterval(refresh,5000);
</script>
</main></body></html>"""
