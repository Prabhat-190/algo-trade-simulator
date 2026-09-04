# Algo Trade Simulator

Real-time transaction cost simulator. Takes L2 orderbook data and estimates fees, slippage and market impact for a market order.

Doesn't place trades. Just a pre-trade cost tool with a Dash UI.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m trading.src.main
```

Then open http://localhost:8050

Docker:

```bash
docker compose up --build
```

http://localhost:8080

No redis / api keys needed. It generates a fake book if nothing else is connected.

## Railway

1. New project, point it at this repo
2. It uses the Dockerfile + railway.toml
3. Add a public domain under Settings -> Networking

Health check is `/healthz`. Don't set `REDIS_HOST=localhost` on Railway.

Optional:
- Redis plugin if you want saved projects to persist
- extra service: `python -m trading.data_feeder` for live crypto data

## Feed

`FEED_SOURCE` (default `auto`):

- `auto` - redis if available, otherwise synthetic
- `synthetic` - always fake data
- `websocket` - connect to `WEBSOCKET_URI` directly
- `redis` - redis only

## Env

See `.env.example`. Main ones:

| var | default |
| --- | --- |
| PORT | 8050 |
| FEED_SOURCE | auto |
| SYMBOL | BTC-USDT |
| REDIS_URL | (optional) |
| WEB_CONCURRENCY | 1 |

Keep workers at 1 unless redis is set, otherwise saved projects wont be shared across workers.

## Endpoints

- `/` dashboard
- `/healthz` liveness
- `/readyz` 200 once market data is flowing

## Tests

```bash
pip install -r requirements-dev.txt
pytest
ruff check .
```

## Layout

```
trading/
  data_feeder.py
  stock_data_feeder.py
  tests/
  src/
    app.py
    main.py
    config.py
    data/          # orderbook, redis, synthetic feed, ws client
    models/        # fees, slippage, impact, maker/taker, simulator
    services/      # feed manager + shared state
    ui/            # dash layout / callbacks / css
```

## SkillUp / IBM Bob

`IBM_BOB.md` is the write-up of how IBM Bob was used (Plan / Ask / Agent).  
Slides for judges: `docs/hackathon/Algo_Trade_Simulator.pptx`

## License

MIT
