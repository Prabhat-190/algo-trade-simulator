# SkillUp form — copy/paste

Solo submission. One person fills the form.

**Full Name:** Prabhat Kumar  
**Phone:** 7367905043  
**Email:** sauravsandilya7367905043@gmail.com  
**Team Name:** TradeSim  
**College Name:** Indian Institute of Technology, Kharagpur  
**Project Name:** Algo Trade Simulator  

**Team Member 1:** sauravsandilya7367905043@gmail.com  
**Team Member 2–5:** leave blank

**GitHub:** https://github.com/Prabhat-190/algo-trade-simulator  

**PPT:** upload `docs/hackathon/Algo_Trade_Simulator.pptx` to Google Drive, set “Anyone with the link can view”, paste that URL.

---

## Problem Statement & Solution Statement

Traders and students who test strategies usually see only the mid price. They do not see what a market order actually costs. Slippage, exchange fees, and market impact sit on top of the quote. A small order on a liquid book may cost almost nothing. The same notional on a thin book, or during a wide spread, can erase the edge of the strategy. Spreadsheets and backtests that assume a fill at mid hide this. Live trading then looks worse than the backtest, and it is hard to tell whether the strategy failed or the execution cost did.

A safe way to study this is also missing. Connecting to a live exchange, storing credentials, and running several services just to see a cost number is more setup than most people will do. If a demo dies when Redis or a websocket is down, it is useless for teaching or judging.

Algo Trade Simulator is a pre-trade cost tool I built as a solo project. It never places an order. It takes a live or synthetic L2 order book and estimates expected slippage, fees, Almgren–Chriss style market impact, maker/taker mix, and net cost for a chosen size, side, fee tier, and volatility.

The dashboard is a Dash app: ticker (mid, spread, imbalance, depth), strategy presets (market order, scalping, swing, large-order impact), depth and cost charts, and a short history of simulations. Named scenarios can be saved when Redis is available.

To stay usable without a market-data stack, the app has an in-process feed manager. FEED_SOURCE=auto uses Redis if it is configured, otherwise a synthetic book so the UI is never empty. That is what makes a single Docker/Railway service work for a demo. Health endpoints (/healthz, /readyz) support that deploy.

Models are the usual TCA pieces: fee schedule by VIP tier, a slippage estimate (regression when trained, heuristic otherwise), participation-based market impact, and a maker/taker model. Bad books (one-sided or zero spread) are flagged instead of producing a fake fill.

The result is a working prototype I can run locally or in Docker, change size and side, and see why two trades with the same notional do not cost the same. It is a cost microscope, not a broker.

---

## Technology Used – IBM Bob

Paste the body of `/IBM_BOB.md` from “IBM Bob is the AI development partner” through “What Bob did not do”. That write-up is under 1000 words. Or paste this shorter version:

I used IBM Bob through IBM SkillsBuild as the required development partner on Algo Trade Simulator (solo project).

In Plan mode I asked Bob to trace the path from an L2 order book to a net-cost number, and to list what fails if Redis or a live websocket is missing. That plan is what the repo does now: TradeSimulator owns the models, FeedManager owns the data source, and a synthetic book keeps the UI alive when nothing else is connected.

In Ask mode I checked two model bugs. Slippage was a per-unit offset that the UI treated as a total dollar cost, so a $100 order looked far too expensive. Market impact was a flat 1% of notional. I kept Bob’s unit fix and a participation-based Almgren–Chriss split, and rejected treating L2 depth as average daily volume.

In Agent mode Bob helped land the files judges can open: synthetic_feed.py, feed_manager.py, config.py (Redis off unless set), redis_bus.py (no localhost retry on Railway), app.py (healthz/readyz), the Dash split (layout, callbacks, figures, theme.css), Dockerfile, and the pytest suite. When Railway’s health check timed out, we stopped hanging on unconfigured Redis. When the deployed page lost its CSS, we stopped using a Bootstrap CDN and served assets from this origin.

I accepted the factory, the synthetic fallback, and the model unit fixes. I rejected mandatory Redis, multi-worker Gunicorn without a shared store, and CDN CSS.

Bob did not invent the product and does not place trades. A longer file-by-file note is in IBM_BOB.md in the public repo.

---

## Additional Information

Solo submission. I am the only team member.

Track fit: financial literacy / developer tools — a pre-trade cost simulator so hidden execution cost is visible before a backtest is treated as truth.

Stack: Python, Dash, Plotly, Gunicorn, Docker, Railway. Redis and websocket feeds are optional. Default FEED_SOURCE=auto uses a synthetic L2 book so the container is self-contained.

The app does not place trades and does not need exchange API keys for the demo.

Repo: https://github.com/Prabhat-190/algo-trade-simulator  
IBM Bob write-up: https://github.com/Prabhat-190/algo-trade-simulator/blob/main/IBM_BOB.md  
Run: `python -m trading.src.main` then http://localhost:8050
