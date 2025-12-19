from mymodule.analytics.domain.entities.client import Client
from mymodule.analytics.infrastructure.abstract_clients_repository import (
    AbstractClientsRepository,
)
from mymodule.common.infrastructure.abstract_engine import AbstractEngine


class ClientsRepository(AbstractClientsRepository):
    def __init__(self, engine: AbstractEngine) -> None:
        self._engine = engine

    def list(self) -> list[Client]:
        clients_rows = self._engine.query("SELECT * from public.clients")

        clients_list = [
            Client(
                id=row.id,
                active=row.active,
                prediction_horizon=row.prediction_horizon,
                airport=row.airport,
                weather=row.weather,
                lead_time=row.lead_time,
            )
            for row in clients_rows
        ]

        return clients_list

    def get(self, entity: Client) -> Client:
        ...

    def add(self, entity: Client) -> Client:
        ...

    def remove(self, entity: Client) -> Client:
        ...

    def update(self, entity: Client) -> Client:
        ...
