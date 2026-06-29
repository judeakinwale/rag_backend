from datetime import datetime
from rag_packages.contracts.dto.shared_dto import BaseDTO
from azure.identity.aio import ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.users.users_request_builder import UsersRequestBuilder


class SharepointConfig(BaseDTO):
    tenant_id: str
    client_id: str
    client_secret: str
    site_url: str | None = None


# interact with sharepoint using graph
class SharepointService:
    def __init__(self, config: SharepointConfig):
        self.token: str
        self.credential = ClientSecretCredential(
            tenant_id=config.tenant_id,
            client_id=config.client_id,
            client_secret=config.client_secret,
        )
        self.graph_client = GraphServiceClient(self.credential)
        self.site_url = config.site_url

    async def get_sharepoint_site_document_libraries(self):
        pass

    async def get_sharepoint_site_documents(
        self, library_ids: list[str], modified_since: datetime | None = None
    ):
        pass

    async def get_sharepoint_site_document(self, document_id: str):
        pass
