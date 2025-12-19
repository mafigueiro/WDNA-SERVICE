import os
from pathlib import Path

import pytest

from mymodule.common.configuration.config import DBConfig, LoggingConfig


@pytest.fixture(name="clean_environment", autouse=True)
def fixture_clean_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Provide a testing environemnt free of environment variables and env files"""
    for key in os.environ:
        monkeypatch.delenv(key)
    os.chdir(tmp_path)


@pytest.fixture(name="conn")
def fixture_conn():
    return DBConfig(
        dialect="mysql",
        driver="pymysql",
        username="l33tH4cker",
        password="swordfish",
        host="10.1.1.123",
        port="5050",
        database="database1",
    )


class TestDBConfig:
    def test_config_generates_correct_string(self, conn: DBConfig):
        assert str(conn) == "mysql://l33tH4cker:swordfish@10.1.1.123:5050/database1"

    def test_config_generates_correct_string_driver(self, conn: DBConfig):
        assert (
            conn.str_with_driver
            == "mysql+pymysql://l33tH4cker:swordfish@10.1.1.123:5050/database1"
        )

    def test_config_cant_generate_driver_string_with_no_driver(self):
        with pytest.raises(ValueError) as exc_info:
            db_config = DBConfig(
                dialect="mysql",
                # no driver
                username="hacker",
                password="swordfish",
                host="10.1.1.123",
                port="5050",
                database="database1",
            )
            db_config.str_with_driver  # pylint: disable=pointless-statement
        assert "driver" in str(exc_info)

    def test_config_throws_exception_on_missing_field(self):
        with pytest.raises(ValueError) as exc_info:
            DBConfig(
                dialect="mysql",
                # driver is optional
                username="hacker",
                password="swordfish",
                # missing required field host, this will raise
                port="5050",
                database="database1",
            )  # type: ignore
        assert "host" in str(exc_info)


class TestLoggingConfig:
    def test_logging_config_loads_from_env_variables(self):
        os.environ["LOG_LEVEL"] = "DEBUG"
        config = LoggingConfig()
        assert config.level == "DEBUG"

    def test_logging_config_loads_from_env_file(self, tmp_path: Path):
        env_file_content = "LOG_LEVEL=WARNING"
        env_file_path = tmp_path / ".env"
        env_file_path.write_text(env_file_content)
        config = LoggingConfig(_env_file=env_file_path)  # type: ignore
        assert config.level == "WARNING"

    def test_logging_config_looks_for_dotenv_by_default(self, tmp_path: Path):
        env_file_content = "LOG_LEVEL=CRITICAL"
        env_file_path = tmp_path / ".env"
        env_file_path.write_text(env_file_content)
        os.chdir(tmp_path)
        config = LoggingConfig()
        assert config.level == "CRITICAL"

    def test_env_variables_beat_env_files(self, tmp_path: Path):
        os.environ["LOG_LEVEL"] = "ERROR"

        env_file_content = "LOG_LEVEL=WARNING"
        env_file_path = tmp_path / ".env"
        env_file_path.write_text(env_file_content)

        config = LoggingConfig(_env_file=env_file_path)  # type: ignore
        assert config.level == "ERROR"

    def test_logging_config_invalid_level_raises_error(self):
        os.environ["LOG_LEVEL"] = "THIS_IS_NOT_A_VALID_LOG_LEVEL"
        with pytest.raises(Exception) as exc_info:
            LoggingConfig()
        assert "Input should be 'CRITICAL', 'ERROR', 'WARNING'" in str(exc_info)
