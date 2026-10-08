# Deploy with GitHub + Render

## 1. GitHub

Create an empty repository:

`https://github.com/new`

Recommended name:

`solana-memecoin-agent`

Owner:

`gn3b0fx9`

Do not add a README/license/gitignore there because this package already contains them.

Then upload these files, or push them using Git.

## 2. Render

Create a Render account and connect GitHub.

Choose:

**New → Blueprint**

Select:

`gn3b0fx9/solana-memecoin-agent`

Render will read `render.yaml`.

The service will use Docker and listen on Render's `$PORT`.

## 3. Open on iPhone

After deployment, Render gives an HTTPS address.

Open it in Safari.

You can use **Share → Add to Home Screen** to make the dashboard feel like an app.

## 4. Security

Before making the dashboard public:
- add authentication;
- do not expose private keys;
- keep live trading disabled;
- keep paper mode clearly visible.

## 5. Free-tier caveat

A free web service may sleep when idle. It is therefore suitable for development/dashboard testing, not a guarantee of a continuously running autonomous trader.

For continuous paper scanning, the next step is a separate scheduled worker/cron service or another free/low-cost runtime.
