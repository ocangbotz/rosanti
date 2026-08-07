from app.config import Settings
from app.services.broker.factory import create_broker_gateway
from app.services.broker.mock_gateway import MockGateway
from app.services.broker.mt5_gateway import MT5Gateway


def test_mock_mode_returns_mock_gateway():
    settings = Settings(broker_mode="mock")
    gateway = create_broker_gateway(settings)
    assert isinstance(gateway, MockGateway)


def test_mt5_mode_returns_mt5_gateway():
    settings = Settings(broker_mode="mt5")
    gateway = create_broker_gateway(settings)
    assert isinstance(gateway, MT5Gateway)
    assert gateway.is_connected is False
