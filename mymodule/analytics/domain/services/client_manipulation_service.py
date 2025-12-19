from mymodule.analytics.domain.entities.client import Client


class ClientManipulationService:
    def extract_names(self, clients: list[Client]) -> list[str]:
        return [client.id for client in clients]
