# Solana Memecoin Agent

Paper-trading AI/automation prototype for a €20 Solana memecoin portfolio.

## Current mode: PAPER ONLY

This repository does not contain wallet keys and does not place real orders.

### Stack
- Python + FastAPI
- Mobile-first dashboard
- Docker
- Render deployment
- Public market-data adapter placeholder
- Risk engine
- Paper portfolio

### Risk defaults
- Starting balance: €20
- Max position: €2
- Minimum cash reserve: €8
- Maximum daily paper loss: €1
- Maximum simultaneous positions: 4
- No leverage
- Kill switch

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
```

Open http://127.0.0.1:8000

## Render

This repository includes `Dockerfile` and `render.yaml`.

1. Create a GitHub repository named `solana-memecoin-agent` under your GitHub account.
2. Upload/push this repository.
3. In Render, choose New > Blueprint.
4. Connect the GitHub repository.
5. Render reads `render.yaml` and creates the web service.
6. Open the HTTPS URL on Safari.

## Important

The Render free service can sleep when idle. Therefore this version is for dashboard/paper testing, not guaranteed 24/7 trading.

Never commit:
- seed phrases
- private keys
- exchange API keys
- `.env` files

Before any live trading, add authenticated storage, real Solana market data, token security checks, transaction simulation, slippage limits and a separate trading worker.
