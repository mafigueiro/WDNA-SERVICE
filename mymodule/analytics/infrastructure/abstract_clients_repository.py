from abc import ABC, abstractmethod

from mymodule.analytics.domain.entities.client import Client
from mymodule.common.infrastructure.abstract_repository import (
    AbstractRepository,
)


class AbstractClientsRepository(AbstractRepository, ABC):
    @abstractmethod
    def list(self) -> list[Client]:
        pass

    @abstractmethod
    def get(self, entity: Client) -> Client:
        pass

    @abstractmethod
    def add(self, entity: Client) -> Client:
        pass

    @abstractmethod
    def remove(self, entity: Client) -> Client:
        pass

    @abstractmethod
    def update(self, entity: Client) -> Client:
        pass
