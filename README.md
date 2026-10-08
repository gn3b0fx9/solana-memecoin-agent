# Solana Memecoin Agent — V2 PAPER

This version replaces synthetic DEMO-A/B/C data with real Solana market data while keeping trading disabled.

## Data flow
- DEX Screener: discovers recent Solana token profiles and pair market data.
- Helius RPC: reads SPL mint account data for mint/freeze authority checks.
- Risk engine: deterministic score; no AI can override it.
- FastAPI/Render: mobile dashboard.
- GitHub Actions: triggers a paper scan every 10 minutes.

## Safety
`PAPER_MODE=true` is mandatory for this phase. No wallet, signing key, Jupiter swap execution, or withdrawal capability is included.

## GitHub secret
Add `RENDER_SCAN_URL` with your Render service URL, e.g. `https://YOUR-SERVICE.onrender.com`.

## Important limitation
Render Free uses ephemeral local storage. `paper_state.json` is therefore not a durable trading journal. For a multi-day experiment, add a free persistent database before treating P/L history as authoritative.
