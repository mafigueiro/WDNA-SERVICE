import logging
from typing import Optional

from mymodule.analytics.domain.services.client_manipulation_service import (
    ClientManipulationService,
)
from mymodule.analytics.infrastructure.abstract_clients_repository import (
    AbstractClientsRepository,
)
from mymodule.common.usecases.base import BaseUseCase


class ListClientsUseCase(BaseUseCase):
    def __init__(
        self,
        clients_repository: AbstractClientsRepository,
        manipulation_service: ClientManipulationService,
    ):
        super().__init__()

        self._clients_repository = clients_repository
        self._manipulation_service = manipulation_service
        self._result = None

    @property
    def result(self) -> Optional[list[str]]:
        return self._result

    def execute(self):
        logging.info("Running say hello use case")
        client_list = self._clients_repository.list()

        self._result = self._manipulation_service.extract_names(client_list)
