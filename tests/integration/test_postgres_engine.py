import pytest

from mymodule.common.configuration.config import DBConfig
from mymodule.common.infrastructure.postgres_engine import PostgresEngine


class TestPostgresEngine:
    @pytest.mark.skip(reason="no way of currently testing this")
    def test_engine_can_connect_to_database(self):
        engine = PostgresEngine(
            config=DBConfig(
                dialect="test",
                username="test",
                password="test",
                host="test",
                port="test",
                database="test",
            )
        )
        connected = engine.test_connection()
        assert connected
