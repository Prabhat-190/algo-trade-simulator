"""
Trading project persistence for reusable simulation setups.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TradingProject:
    """A saved trading simulation setup."""

    name: str
    strategy: str
    exchange: str
    market_type: str
    symbol: str
    side: str
    quantity_usd: float
    volatility: float
    fee_tier: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TradingProject":
        return cls(
            name=str(data.get("name", "Untitled Project")).strip() or "Untitled Project",
            strategy=str(data.get("strategy", "market_order")),
            exchange=str(data.get("exchange", "OKX")),
            market_type=str(data.get("market_type", "spot")),
            symbol=str(data.get("symbol", "BTC-USDT")),
            side=str(data.get("side", "buy")),
            quantity_usd=float(data.get("quantity_usd", 100) or 100),
            volatility=float(data.get("volatility", 0.01) or 0.01),
            fee_tier=str(data.get("fee_tier", "VIP0")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TradingProjectStore:
    """
    Stores trading projects in Redis when available, with an in-memory fallback.

    Redis keeps saved project setups available to every Gunicorn worker or dashboard
    replica behind the load balancer. If Redis is unavailable, the dashboard still
    works but saved projects live only in the current process.
    """

    redis_key = "trading_projects"

    def __init__(self, redis_client: Optional[Any] = None):
        self.redis_client = redis_client
        self._memory: Dict[str, Dict[str, Any]] = {}
        self.save(
            TradingProject(
                name="BTC Scalping Demo",
                strategy="market_order",
                exchange="OKX",
                market_type="spot",
                symbol="BTC-USDT",
                side="buy",
                quantity_usd=100.0,
                volatility=0.01,
                fee_tier="VIP0",
            )
        )

    def save(self, project: TradingProject) -> None:
        payload = json.dumps(project.to_dict())
        self._memory[project.name] = project.to_dict()
        if self.redis_client is None:
            return
        try:
            self.redis_client.hset(self.redis_key, project.name, payload)
        except Exception as exc:
            logger.warning("Unable to save project to Redis; using memory fallback: %s", exc)

    def get(self, name: str) -> Optional[TradingProject]:
        if not name:
            return None
        payload = None
        if self.redis_client is not None:
            try:
                payload = self.redis_client.hget(self.redis_key, name)
            except Exception as exc:
                logger.warning("Unable to load project from Redis; using memory fallback: %s", exc)
        if payload:
            return TradingProject.from_dict(json.loads(payload))
        data = self._memory.get(name)
        return TradingProject.from_dict(data) if data else None

    def list_projects(self) -> List[Dict[str, str]]:
        names = set(self._memory.keys())
        if self.redis_client is not None:
            try:
                names.update(self.redis_client.hkeys(self.redis_key))
            except Exception as exc:
                logger.warning("Unable to list projects from Redis; using memory fallback: %s", exc)
        return [{"label": name, "value": name} for name in sorted(names)]
