# SkillUp Hackathon — complete form guide

Use this file while filling the **Project Submission** form. Copy each block into the matching field.

**PPT file (upload to Google Drive):** `docs/hackathon/Algo_Trade_Simulator.pptx` (12 slides, includes dashboard screenshot)

---

## Field-by-field map

| Form field | What to paste |
| --- | --- |
| Full Name | Prabhat Kumar |
| Phone | 7367905043 |
| Email | sauravsandilya7367905043@gmail.com |
| Team Name | TradeSim |
| College Name | Indian Institute of Technology, Kharagpur |
| Project Name | Algo Trade Simulator |
| Team Member 1 | sauravsandilya7367905043@gmail.com |
| Team Member 2–5 | *(leave blank — solo submission)* |
| Problem Statement & Solution | Section below (~368 words) |
| Technology Used – IBM Bob | Section below (~891 words) |
| GitHub Repository | https://github.com/Prabhat-190/algo-trade-simulator |
| PPT / Video Demo Link | https://github.com/Prabhat-190/algo-trade-simulator/blob/main/docs/hackathon/Algo_Trade_Simulator.pptx |
| Additional Information | Section below |

---

## Problem Statement & Solution Statement

*(paste into “Problem Statement & Solution Statement”, max 500 words)*

Traders and students who test strategies usually see only the mid price. They do not see what a market order actually costs. Slippage, exchange fees, and market impact sit on top of the quote. A small order on a liquid book may cost almost nothing. The same notional on a thin book, or during a wide spread, can erase the edge of the strategy. Spreadsheets and backtests that assume a fill at mid hide this. Live trading then looks worse than the backtest, and it is hard to tell whether the strategy failed or the execution cost did.

A safe way to study this is also missing. Connecting to a live exchange, storing credentials, and running several services just to see a cost number is more setup than most people will do. If a demo dies when Redis or a websocket is down, it is useless for teaching or judging.

Algo Trade Simulator is a pre-trade cost tool I built as a solo project. It never places an order. It takes a live or synthetic L2 order book and estimates expected slippage, fees, Almgren–Chriss style market impact, maker/taker mix, and net cost for a chosen size, side, fee tier, and volatility.

The dashboard is a Dash app: ticker (mid, spread, imbalance, depth), strategy presets (market order, scalping, swing, large-order impact), depth and cost charts, and a short history of simulations. Named scenarios can be saved when Redis is available.

To stay usable without a market-data stack, the app has an in-process feed manager. FEED_SOURCE=auto uses Redis if it is configured, otherwise a synthetic book so the UI is never empty. That is what makes a single Docker/Railway service work for a demo. Health endpoints (/healthz, /readyz) support that deploy.

Models are the usual TCA pieces: fee schedule by VIP tier, a slippage estimate (regression when trained, heuristic otherwise), participation-based market impact, and a maker/taker model. Bad books (one-sided or zero spread) are flagged instead of producing a fake fill.

The result is a working prototype I can run locally or in Docker, change size and side, and see why two trades with the same notional do not cost the same. It is a cost microscope, not a broker.

---

## Technology Used – IBM Bob

*(paste into “Technology Used – IBM Bob”, max 1000 words)*

IBM Bob is the AI development partner required for this hackathon. I used it as a second pair of hands across planning, coding, review, and test work on this repo. The cost models and the product idea are mine. Bob was used to move faster on structure, deploy, and cleanup.

Access

I used IBM Bob through the IBM SkillsBuild / SkillUp Hackathon student access. Work was done in the three modes Bob exposes: Plan (map the data path and decide what a single Railway service must do), Ask (check the Almgren–Chriss and slippage math before changing code), and Agent (edit files, add tests, and fix Railway / UI breakage).

Plan mode

The first useful session was planning, not code. I asked Bob to walk the path from an L2 book to a net-cost number, and to list what would break if Redis or a live websocket was missing.

That produced a short plan I actually followed:

1. Keep TradeSimulator as the only place that runs fees, slippage, impact, and maker/taker.
2. Put feed choice in one place (FeedManager) instead of starting extra containers for a demo.
3. If Redis is not set, skip it. Do not retry localhost:6379 during startup.
4. Always have a synthetic book so the dashboard is never empty.
5. Split the old single dashboard file into layout, callbacks, figures, and CSS.

That is why FEED_SOURCE=auto is the default and why Railway can run one Docker image.

Ask mode

Two model questions were checked in Ask before I changed production code.

Slippage units. The old fallback returned a per-unit price offset, but the UI treated it as a total dollar cost. A $100 order looked like it slipped several dollars. Bob confirmed the consumer expected quote-currency totals. The fix is in trading/src/models/slippage_model.py: the heuristic now does concession × quantity.

Market impact. Impact was a flat 1% of notional, so a tiny order and a large order paid the same fraction. Ask mode was used to sanity-check a participation-based Almgren–Chriss split (square-root temporary impact, linear permanent). That is what trading/src/models/market_impact.py does now.

I did not take every suggestion. Bob at one point treated orderbook depth as if it were average daily volume. I kept a scale factor (DEPTH_TO_DAILY_VOLUME_FACTOR) instead of pretending L2 depth is ADV.

Agent mode

These are the changes I applied with Bob in the repo (files you can open):

Single-service demo: trading/src/data/synthetic_feed.py (local L2 book, no exchange keys), trading/src/services/feed_manager.py (Redis / websocket / synthetic, with fallback), trading/src/config.py (Redis is off unless REDIS_URL or REDIS_HOST is set), trading/src/data/redis_bus.py (return None immediately when Redis is not configured).

App shape: trading/src/app.py (create_app factory, /healthz and /readyz), trading/src/ui/layout.py, callbacks.py, figures.py (dashboard split), trading/src/ui/assets/theme.css (theme served from this origin, no CDN).

Deploy: Dockerfile (Gunicorn, WEB_CONCURRENCY=1), railway.toml (health check, longer cold-start timeout). Railway UI bug: Bootstrap from a CDN failed behind HTTPS. CSS is local now. ProxyFix is on so the app sees the real scheme.

Tests: trading/tests/ — orderbook, simulator, feed manager, config, app health.

What I accepted vs what I rejected

Accepted: application factory instead of building the Dash app at import time; synthetic fallback so a judge can open the UI without Redis; skip Redis on boot when nobody configured it; slippage as a total cost, impact as a function of participation; pytest + ruff in CI.

Rejected: making Redis mandatory; treating L2 depth as ADV; pulling Bootstrap from a public CDN on the deployed site; multi-worker Gunicorn without a shared store.

Workflow I actually used

1. Plan the feed and deploy constraints.
2. Ask about the two model bugs.
3. Agent: implement synthetic feed, config, health routes, UI split.
4. Run the app locally, then deploy to Railway.
5. When the deploy failed or the page looked unstyled, paste the symptom back into Ask/Agent and fix the specific file.
6. Agent: tests for the new paths.

What Bob did not do

Bob did not invent the product. It did not place trades, call a broker, or replace the models with a chatbot. I still chose the defaults, kept or dropped patches, and ran the app.

The live path a judge should see: (1) Synthetic (or live) L2 book updates the ticker. (2) User sets size, side, fee tier, volatility. (3) TradeSimulator returns slippage, fees, impact, maker/taker, net cost. (4) Charts update. Nothing is sent to an exchange.

Full file-by-file note: IBM_BOB.md in the public repo.

---

## GitHub Repository

https://github.com/Prabhat-190/algo-trade-simulator

Judges can also open the IBM Bob document directly:
https://github.com/Prabhat-190/algo-trade-simulator/blob/main/IBM_BOB.md

---

## PPT / Video Demo Link

Public link (no Google Drive needed):

https://github.com/Prabhat-190/algo-trade-simulator/blob/main/docs/hackathon/Algo_Trade_Simulator.pptx

12 slides, under the 20-slide limit. Includes dashboard screenshot.

### Slide outline (what judges will see)

1. Title — Algo Trade Simulator / TradeSim / IIT Kharagpur
2. Problem — hidden execution cost
3. Solution — pre-trade cost microscope
4. Live dashboard screenshot
5. Architecture — FeedManager → TradeSimulator → Dash UI
6. Key features — slippage, fees, impact, maker/taker
7. Strategy presets
8. IBM Bob — Plan / Ask / Agent
9. Deploy — Docker, Railway, health checks
10. Tech stack
11. Demo — how to run locally
12. Thank you + GitHub link

*(Optional video instead of PPT: record ≤3 min with QuickTime → upload to YouTube unlisted or Drive. PPT alone is enough.)*

---

## Additional Information

Solo submission. I am the only team member (Prabhat Kumar, IIT Kharagpur).

Track fit: financial literacy / developer tools — a pre-trade cost simulator so hidden execution cost is visible before a backtest is treated as truth.

Stack: Python, Dash, Plotly, Gunicorn, Docker, Railway. Redis and websocket feeds are optional. Default FEED_SOURCE=auto uses a synthetic L2 book so the container is self-contained.

The app does not place trades and does not need exchange API keys for the demo.

Run locally: python -m trading.src.main then open http://localhost:8050

---

## Pre-submit checklist

- [ ] GitHub repo is **public** and opens without login
- [ ] `IBM_BOB.md` is visible at repo root
- [ ] PPT uploaded to Google Drive with **Anyone with the link** access
- [ ] All form fields filled; Team Member 2–5 left blank
- [ ] Click every link once in an incognito window before Submit
