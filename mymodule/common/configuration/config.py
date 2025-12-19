import logging
from pathlib import Path
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

from mymodule.common.errors.application_exception import ApplicationException


class InvalidConfig(ApplicationException):
    def __init__(
        self,
        description: str,
        *args: object,
        root_exception: Optional[Exception] = None,
    ) -> None:
        self.description = description

        super().__init__(root_exception, *args)


def configure_logging() -> None:
    config = LoggingConfig()

    root_logger = logging.getLogger()

    # removes default logging handler
    root_logger.handlers.clear()
    root_logger.setLevel(config.level)
    log_formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
        datefmt="%d-%m-%Y:%H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)
    root_logger.addHandler(stream_handler)

    log_file = Path(config.file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)


class LoggingConfig(BaseSettings):
    level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"] = "INFO"
    file: str = "./app.log"

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="LOG_", extra="ignore"
    )


class DBConfig(BaseSettings):
    dialect: str
    driver: Optional[str] = None
    username: str
    password: str
    host: str
    port: str
    database: str

    def _string_helper(self, prefix) -> str:
        return (
            f"{prefix}://"
            f"{self.username}:{self.password}"
            f"@{self.host}:{self.port}"
            f"/{self.database}"
        )

    @property
    def str_with_driver(self) -> str:
        """Computes the string representation with a driver."""
        if not getattr(self, "driver"):
            raise ValueError(
                "You need to define a driver in your environment file, named DB_DRIVER."
            )
        return self._string_helper(prefix=f"{self.dialect}+{self.driver}")

    def __str__(self):
        return self._string_helper(prefix=self.dialect)

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="DB_", populate_by_name=True, extra="ignore"
    )
