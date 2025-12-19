from typing import Optional

from mymodule.analytics.domain.services.client_manipulation_service import (
    ClientManipulationService,
)
from mymodule.analytics.infrastructure.clients_repository import ClientsRepository
from mymodule.analytics.usecases.list_clients import ListClientsUseCase
from mymodule.common.infrastructure.postgres_engine import PostgresEngine


class AnalyticsController:
    def __init__(self) -> None:
        self._engine = PostgresEngine()
        self._clients_repository = ClientsRepository(self._engine)
        self._manipulation_service = ClientManipulationService()

    def list_clients(self) -> Optional[list[str]]:
        uc = ListClientsUseCase(self._clients_repository, self._manipulation_service)
        uc.execute()

        return uc.result
