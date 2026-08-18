"""Tests for trading project persistence."""
from __future__ import annotations

import pytest

from trading.src.models.trading_project import TradingProject, TradingProjectStore

PROJECT_PAYLOAD = {
    "name": "ETH Swing Plan",
    "strategy": "swing",
    "exchange": "OKX",
    "market_type": "spot",
    "symbol": "ETH-USDT",
    "side": "sell",
    "quantity_usd": 2500,
    "volatility": 0.02,
    "fee_tier": "VIP1",
}


def test_save_and_load_from_memory():
    store = TradingProjectStore(redis_client=None)
    store.save(TradingProject.from_dict(PROJECT_PAYLOAD))

    loaded = store.get("ETH Swing Plan")
    assert loaded is not None
    assert loaded.symbol == "ETH-USDT"
    assert loaded.strategy == "swing"
    assert loaded.quantity_usd == 2500


def test_project_options_are_dropdown_ready():
    options = TradingProjectStore(redis_client=None).list_projects()

    assert len(options) >= 1
    assert set(options[0]) == {"label", "value"}


def test_missing_project_returns_none():
    store = TradingProjectStore(redis_client=None)
    assert store.get("does-not-exist") is None
    assert store.get("") is None


def test_from_dict_applies_defaults():
    project = TradingProject.from_dict({})

    assert project.name == "Untitled Project"
    assert project.strategy == "market_order"
    assert project.quantity_usd == 100
    assert project.volatility == 0.01


def test_blank_name_falls_back_to_placeholder():
    assert TradingProject.from_dict({"name": "   "}).name == "Untitled Project"


def test_round_trip_through_dict():
    project = TradingProject.from_dict(PROJECT_PAYLOAD)
    assert TradingProject.from_dict(project.to_dict()) == project


def test_redis_failure_falls_back_to_memory():
    class BrokenRedis:
        def hset(self, *_args, **_kwargs):
            raise RuntimeError("redis down")

        def hget(self, *_args, **_kwargs):
            raise RuntimeError("redis down")

        def hkeys(self, *_args, **_kwargs):
            raise RuntimeError("redis down")

    store = TradingProjectStore(redis_client=BrokenRedis())
    store.save(TradingProject.from_dict(PROJECT_PAYLOAD))

    # Saving and loading still work through the in-memory fallback.
    assert store.get("ETH Swing Plan").symbol == "ETH-USDT"
    assert any(option["value"] == "ETH Swing Plan" for option in store.list_projects())


def test_redis_backed_store_prefers_redis():
    class FakeRedis:
        def __init__(self):
            self.hash: dict[str, str] = {}

        def hset(self, _key, field, value):
            self.hash[field] = value

        def hget(self, _key, field):
            return self.hash.get(field)

        def hkeys(self, _key):
            return list(self.hash)

    fake = FakeRedis()
    store = TradingProjectStore(redis_client=fake)
    store.save(TradingProject.from_dict(PROJECT_PAYLOAD))

    assert "ETH Swing Plan" in fake.hash
    assert store.get("ETH Swing Plan").fee_tier == "VIP1"


@pytest.mark.parametrize("quantity", [0, None, ""])
def test_falsy_quantity_uses_default(quantity):
    assert TradingProject.from_dict({"quantity_usd": quantity}).quantity_usd == 100
