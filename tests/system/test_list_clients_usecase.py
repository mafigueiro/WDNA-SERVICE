from mymodule.wdna.domain.entities.client import Client
from mymodule.wdna.domain.services.client_manipulation_service import (
    ClientManipulationService,
)
from mymodule.wdna.infrastructure.abstract_clients_repository import (
    AbstractClientsRepository,
)
from mymodule.wdna.usecases.list_clients import ListClientsUseCase


class MockClientRespository(AbstractClientsRepository):
    def list(self) -> list[Client]:
        return [
            Client(
                id="1",
                active=1,
                prediction_horizon="patatas",
                airport=False,
                weather=False,
                lead_time=0,
            )
        ]

    def get(self, entity: Client) -> Client:
        pass

    def add(self, entity: Client) -> Client:
        pass

    def remove(self, entity: Client) -> Client:
        pass

    def update(self, entity: Client) -> Client:
        pass


class TestListClientsUseCase:
    def test_retrieves_list_of_clients(self):
        repo = MockClientRespository()
        uc = ListClientsUseCase(repo, ClientManipulationService())
        uc.execute()

        result = uc.result
        assert result is not None
        assert len(result) > 0
