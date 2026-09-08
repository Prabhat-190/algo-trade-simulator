# COPY-PASTE INTO THE FORM — field order

Open the SkillUp submission form. Copy each block below into the matching box.

---

### Full Name
```
Prabhat Kumar
```

### Phone
```
7367905043
```

### Email
```
sauravsandilya7367905043@gmail.com
```

### Team Name
```
TradeSim
```

### College Name
```
Indian Institute of Technology, Kharagpur
```

### Project Name
```
Algo Trade Simulator
```

### Team Member 1
```
sauravsandilya7367905043@gmail.com
```

### Team Member 2, 3, 4, 5
Leave all blank.

---

### Problem Statement & Solution Statement

Traders and students who test strategies usually see only the mid price. They do not see what a market order actually costs. Slippage, exchange fees, and market impact sit on top of the quote. A small order on a liquid book may cost almost nothing. The same notional on a thin book, or during a wide spread, can erase the edge of the strategy. Spreadsheets and backtests that assume a fill at mid hide this. Live trading then looks worse than the backtest, and it is hard to tell whether the strategy failed or the execution cost did.

A safe way to study this is also missing. Connecting to a live exchange, storing credentials, and running several services just to see a cost number is more setup than most people will do. If a demo dies when Redis or a websocket is down, it is useless for teaching or judging.

Algo Trade Simulator is a pre-trade cost tool I built as a solo project. It never places an order. It takes a live or synthetic L2 order book and estimates expected slippage, fees, Almgren–Chriss style market impact, maker/taker mix, and net cost for a chosen size, side, fee tier, and volatility.

The dashboard is a Dash app: ticker (mid, spread, imbalance, depth), strategy presets (market order, scalping, swing, large-order impact), depth and cost charts, and a short history of simulations. Named scenarios can be saved when Redis is available.

To stay usable without a market-data stack, the app has an in-process feed manager. FEED_SOURCE=auto uses Redis if it is configured, otherwise a synthetic book so the UI is never empty. That is what makes a single Docker/Railway service work for a demo. Health endpoints (/healthz, /readyz) support that deploy.

Models are the usual TCA pieces: fee schedule by VIP tier, a slippage estimate (regression when trained, heuristic otherwise), participation-based market impact, and a maker/taker model. Bad books (one-sided or zero spread) are flagged instead of producing a fake fill.

The result is a working prototype I can run locally or in Docker, change size and side, and see why two trades with the same notional do not cost the same. It is a cost microscope, not a broker.

---

### Technology Used – IBM Bob

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

Slippage units. The old fallback returned a per-unit price offset, but the UI treated it as a total dollar cost. A $100 order looked like it slipped several dollars. Bob confirmed the consumer expected quote-currency totals. The fix is in trading/src/models/slippage_model.py: the heuristic now does concession times quantity.

Market impact. Impact was a flat 1% of notional, so a tiny order and a large order paid the same fraction. Ask mode was used to sanity-check a participation-based Almgren–Chriss split (square-root temporary impact, linear permanent). That is what trading/src/models/market_impact.py does now.

I did not take every suggestion. Bob at one point treated orderbook depth as if it were average daily volume. I kept a scale factor instead of pretending L2 depth is ADV.

Agent mode

These are the changes I applied with Bob in the repo: synthetic_feed.py, feed_manager.py, config.py, redis_bus.py, app.py with healthz and readyz, Dash UI split into layout, callbacks, figures, and local theme.css, Dockerfile, railway.toml, and pytest suite. Fixed Railway health-check timeout (no localhost Redis hang) and missing CSS behind HTTPS proxy.

What I accepted: application factory, synthetic fallback, skip unconfigured Redis, slippage as total cost, impact by participation, pytest and ruff in CI.

What I rejected: mandatory Redis, treating L2 depth as ADV, CDN Bootstrap, multi-worker Gunicorn without shared store.

What Bob did not do: invent the product, place trades, or replace models. I chose defaults and ran the app.

Judges can verify: https://github.com/Prabhat-190/algo-trade-simulator/blob/main/IBM_BOB.md

---

### GitHub Repository
```
https://github.com/Prabhat-190/algo-trade-simulator
```

### PPT / Video Demo Link
```
https://github.com/Prabhat-190/algo-trade-simulator/blob/main/docs/hackathon/Algo_Trade_Simulator.pptx
```

### Additional Information

Solo submission. I am the only team member (Prabhat Kumar, IIT Kharagpur).

Track fit: financial literacy / developer tools — pre-trade cost simulator so execution cost is visible before trusting a backtest.

Stack: Python, Dash, Plotly, Gunicorn, Docker, Railway. Redis and websocket feeds are optional. Default FEED_SOURCE=auto uses a synthetic L2 book so the container is self-contained. The app does not place trades and does not need exchange API keys.

Run locally: python -m trading.src.main then http://localhost:8050

IBM Bob write-up: https://github.com/Prabhat-190/algo-trade-simulator/blob/main/IBM_BOB.md

---

## Done. Click Submit.
