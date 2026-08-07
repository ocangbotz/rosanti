from app.config import get_settings
from app.core.constants import Timeframe
from app.services.broker.mock_gateway import MockGateway
from app.services.market_data import MarketDataService


class _CountingGateway(MockGateway):
    def __init__(self, settings):
        super().__init__(settings)
        self.ohlc_calls = 0

    def get_ohlc(self, symbol, timeframe, count):
        self.ohlc_calls += 1
        return super().get_ohlc(symbol, timeframe, count)


def test_repeated_calls_within_ttl_use_cache():
    gateway = _CountingGateway(get_settings())
    gateway.connect()
    service = MarketDataService(gateway, cache_ttl_seconds=60)

    df1 = service.get_ohlc("EURUSD", Timeframe.H1, 100)
    df2 = service.get_ohlc("EURUSD", Timeframe.H1, 100)

    assert gateway.ohlc_calls == 1
    assert df1.equals(df2)


def test_cache_is_bypassed_when_use_cache_false():
    gateway = _CountingGateway(get_settings())
    gateway.connect()
    service = MarketDataService(gateway, cache_ttl_seconds=60)

    service.get_ohlc("EURUSD", Timeframe.H1, 100)
    service.get_ohlc("EURUSD", Timeframe.H1, 100, use_cache=False)

    assert gateway.ohlc_calls == 2


def test_different_cache_keys_do_not_collide():
    gateway = _CountingGateway(get_settings())
    gateway.connect()
    service = MarketDataService(gateway, cache_ttl_seconds=60)

    service.get_ohlc("EURUSD", Timeframe.H1, 100)
    service.get_ohlc("GBPUSD", Timeframe.H1, 100)
    service.get_ohlc("EURUSD", Timeframe.H4, 100)

    assert gateway.ohlc_calls == 3


def test_cache_expires_after_ttl(monkeypatch):
    gateway = _CountingGateway(get_settings())
    gateway.connect()
    service = MarketDataService(gateway, cache_ttl_seconds=0)

    service.get_ohlc("EURUSD", Timeframe.H1, 100)
    service.get_ohlc("EURUSD", Timeframe.H1, 100)

    assert gateway.ohlc_calls == 2


def test_service_connects_gateway_lazily():
    gateway = MockGateway(get_settings())
    assert gateway.is_connected is False
    service = MarketDataService(gateway)
    service.get_account_info()
    assert gateway.is_connected is True
