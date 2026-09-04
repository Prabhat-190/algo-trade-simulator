# How IBM Bob was used

**Project:** Algo Trade Simulator  
**Author:** Prabhat Kumar (solo)  
**College:** Indian Institute of Technology, Kharagpur  
**Hackathon:** SkillUp Hackathon × IBM SkillsBuild

IBM Bob is the AI development partner required for this hackathon. I used it as a second pair of hands across planning, coding, review, and test work on this repo. The cost models and the product idea are mine. Bob was used to move faster on structure, deploy, and cleanup.

## Access

I used IBM Bob through the IBM SkillsBuild / SkillUp Hackathon student access. Work was done in the three modes Bob exposes:

| Mode | What I used it for |
| --- | --- |
| Plan | Map the data path and decide what a single Railway service must do |
| Ask | Check the Almgren–Chriss and slippage math before changing code |
| Agent | Edit files, add tests, and fix Railway / UI breakage |

## Plan mode

The first useful session was planning, not code. I asked Bob to walk the path from an L2 book to a net-cost number, and to list what would break if Redis or a live websocket was missing.

That produced a short plan I actually followed:

1. Keep `TradeSimulator` as the only place that runs fees, slippage, impact, and maker/taker.
2. Put feed choice in one place (`FeedManager`) instead of starting extra containers for a demo.
3. If Redis is not set, skip it. Do not retry `localhost:6379` during startup.
4. Always have a synthetic book so the dashboard is never empty.
5. Split the old single dashboard file into layout, callbacks, figures, and CSS.

That is why `FEED_SOURCE=auto` is the default and why Railway can run one Docker image.

## Ask mode

Two model questions were checked in Ask before I changed production code.

**Slippage units.** The old fallback returned a per-unit price offset, but the UI treated it as a total dollar cost. A $100 order looked like it slipped several dollars. Bob confirmed the consumer expected quote-currency totals. The fix is in `trading/src/models/slippage_model.py`: the heuristic now does concession × quantity.

**Market impact.** Impact was a flat 1% of notional, so a tiny order and a large order paid the same fraction. Ask mode was used to sanity-check a participation-based Almgren–Chriss split (square-root temporary impact, linear permanent). That is what `trading/src/models/market_impact.py` does now.

I did not take every suggestion. Bob at one point treated orderbook depth as if it were average daily volume. I kept a scale factor (`DEPTH_TO_DAILY_VOLUME_FACTOR`) instead of pretending L2 depth is ADV.

## Agent mode

These are the changes I applied with Bob in the repo (files you can open):

**Single-service demo**

- `trading/src/data/synthetic_feed.py` — local L2 book, no exchange keys
- `trading/src/services/feed_manager.py` — Redis / websocket / synthetic, with fallback
- `trading/src/config.py` — Redis is off unless `REDIS_URL` or `REDIS_HOST` is set; leftover `localhost` on Railway is ignored
- `trading/src/data/redis_bus.py` — return `None` immediately when Redis is not configured

**App shape**

- `trading/src/app.py` — `create_app()` factory, `/healthz` and `/readyz`
- `trading/src/ui/layout.py`, `callbacks.py`, `figures.py` — dashboard split
- `trading/src/ui/assets/theme.css` — theme + layout CSS served from this origin (no CDN)

**Deploy**

- `Dockerfile` — Gunicorn, `WEB_CONCURRENCY=1`
- `railway.toml` — health check, longer cold-start timeout
- Railway UI bug: Bootstrap from a CDN failed behind HTTPS. CSS is local now. `ProxyFix` is on so the app sees the real scheme.

**Tests**

- `trading/tests/` — orderbook, simulator, feed manager, config, app health

I also used Agent mode to cut comments that read like a tutorial. The older modules in this repo are short. I kept the new ones in the same tone.

## What I accepted vs what I rejected

Accepted:

- application factory instead of building the Dash app at import time
- synthetic fallback so a judge can open the UI without Redis
- skip Redis on boot when nobody configured it (this was the Railway health-check timeout)
- slippage as a total cost, impact as a function of participation
- pytest + ruff in CI

Rejected:

- making Redis mandatory
- treating L2 depth as ADV
- pulling Bootstrap from a public CDN on the deployed site
- multi-worker Gunicorn without a shared store (saved projects would not match)

## Workflow I actually used

1. Plan the feed and deploy constraints.
2. Ask about the two model bugs.
3. Agent: implement synthetic feed, config, health routes, UI split.
4. Run the app locally, then deploy to Railway.
5. When the deploy failed or the page looked unstyled, paste the symptom back into Ask/Agent and fix the specific file.
6. Agent: tests for the new paths.

Typical prompt shape (paraphrased):

- “Trace how an orderbook frame becomes net cost. Where does this break if Redis is down?”
- “This slippage number does not scale with quantity. Who is treating it as a total?”
- “Railway health check dies on boot. Do not hang on localhost Redis.”
- “Dashboard CSS is missing behind the Railway HTTPS proxy. Serve assets locally.”

## What Bob did not do

Bob did not invent the product. It did not place trades, call a broker, or replace the models with a chatbot. I still chose the defaults, kept or dropped patches, and ran the app.

The live path a judge should see:

1. Synthetic (or live) L2 book updates the ticker.
2. User sets size, side, fee tier, volatility.
3. `TradeSimulator` returns slippage, fees, impact, maker/taker, net cost.
4. Charts update. Nothing is sent to an exchange.

## Repo map

```
trading/src/app.py                 factory + health
trading/src/config.py              env / Redis / feed
trading/src/services/feed_manager.py
trading/src/data/synthetic_feed.py
trading/src/models/simulator.py
trading/src/models/slippage_model.py
trading/src/models/market_impact.py
trading/src/ui/                    Dash UI
```

Run locally: `python -m trading.src.main` then open http://localhost:8050
