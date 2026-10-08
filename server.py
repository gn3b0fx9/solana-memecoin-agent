import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from paper import run_scan, load

app=FastAPI(title="Solana Memecoin Agent — PAPER")

@app.get("/health")
def health(): return {"ok":True,"paper_mode":os.getenv("PAPER_MODE","true").lower()=="true"}

@app.post("/api/scan")
def scan():
    try: return run_scan()
    except Exception as e: return JSONResponse({"ok":False,"error":str(e)},500)

@app.get("/api/state")
def state(): return load()

@app.get("/",response_class=HTMLResponse)
def home():
    s=load(); rows=s.get("candidates",[])
    body="".join(f"<tr><td>{r.get('symbol')}</td><td>{r.get('score')}</td><td>${r.get('price_usd',0):.8g}</td><td>${r.get('liquidity_usd',0):,.0f}</td><td>${r.get('volume_24h_usd',0):,.0f}</td><td>{r.get('price_change_1h',0):.1f}%</td></tr>" for r in rows)
    return f'''<!doctype html><html><meta name="viewport" content="width=device-width,initial-scale=1"><title>Solana Agent</title><style>body{{font-family:system-ui;margin:16px;background:#111;color:#eee}}.card{{background:#1b1b1b;padding:14px;border-radius:14px;margin-bottom:12px}}table{{width:100%;font-size:12px;border-collapse:collapse}}td,th{{padding:7px;border-bottom:1px solid #333;text-align:left}}button{{padding:12px 16px;border:0;border-radius:10px;font-weight:700}}.safe{{color:#6ee7b7}}</style><div class="card"><h2>Solana Memecoin Agent</h2><div class="safe">PAPER MODE — REAL MONEY OFF</div><p>Cash virtual: €{s.get('cash_eur',20):.2f}</p><form method="post" action="/api/scan"><button>Scan agora</button></form></div><div class="card"><h3>Top candidates</h3><table><tr><th>Token</th><th>Score</th><th>Price</th><th>Liquidity</th><th>Vol 24h</th><th>1h</th></tr>{body}</table></div></html>'''
