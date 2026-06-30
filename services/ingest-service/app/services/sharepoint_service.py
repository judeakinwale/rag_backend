import asyncio
from datetime import datetime
from urllib.parse import quote, urlparse

import httpx
from rag_packages.contracts.dto.shared_dto import BaseDTO
from azure.identity.aio import ClientSecretCredential


class SharepointConfig(BaseDTO):
    tenant_id: str
    client_id: str
    client_secret: str
    site_url: str | None = None


# interact with sharepoint using graph
class SharepointService:
    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
    GRAPH_SCOPE = "https://graph.microsoft.com/.default"

    def __init__(self, config: SharepointConfig):
        # self.token: str
        self.credential = ClientSecretCredential(
            tenant_id=config.tenant_id,
            client_id=config.client_id,
            client_secret=config.client_secret,
        )
        self.site_url = config.site_url
        self._site_id: str | None = None

    async def _headers(self) -> dict[str, str]:
        token = await self.credential.get_token(self.GRAPH_SCOPE)
        return {"Authorization": f"Bearer {token.token}"}

    async def _get_json(
        self, client: httpx.AsyncClient, url: str, params: dict | None = None
    ) -> dict:
        response = await client.get(url, headers=await self._headers(), params=params)
        response.raise_for_status()
        return response.json()

    async def _get_paged(
        self, client: httpx.AsyncClient, url: str, params: dict | None = None
    ) -> list[dict]:
        items: list[dict] = []
        next_url: str | None = url
        next_params = params

        while next_url:
            data = await self._get_json(client, next_url, next_params)
            items.extend(data.get("value", []))
            next_url = data.get("@odata.nextLink")
            next_params = None

        return items

    async def _get_site_id(self, client: httpx.AsyncClient) -> str:
        if self._site_id:
            return self._site_id

        if not self.site_url:
            data = await self._get_json(client, f"{self.GRAPH_BASE_URL}/sites/root")
            self._site_id = data["id"]
            return self._site_id

        parsed = urlparse(self.site_url)
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("SharePoint site_url must be an absolute URL")

        path = parsed.path.rstrip("/")
        site_path = f"{hostname}:{path}" if path else hostname
        data = await self._get_json(
            client,
            f"{self.GRAPH_BASE_URL}/sites/{quote(site_path, safe=':/')}",
        )
        self._site_id = data["id"]
        return self._site_id

    # ? specify a schema/dto that describes this or use an existing one
    def _format_document(self, item: dict, library: dict, site: dict) -> dict | None:
        if "file" not in item:
            return None

        name = item.get("name") or ""
        last_modified = item.get("lastModifiedDateTime")
        parent = item.get("parentReference", {})
        parent_path = parent.get("path", "")
        _, _, relative_parent_path = parent_path.partition("root:")
        file_metadata = {
            "sharepoint_id": item.get("id"),
            "drive_id": library.get("id"),
            "etag": item.get("eTag"),
            "ctag": item.get("cTag"),
            "mime_type": item.get("file", {}).get("mimeType"),
            "created_at": item.get("createdDateTime"),
            "last_modified_by": item.get("lastModifiedBy"),
            "created_by": item.get("createdBy"),
            "size": item.get("size"),
        }

        return {
            "name": name,
            "file_url": item.get("webUrl"),
            "library_name": library.get("name"),
            "library_id": library.get("id"),
            "site_url": site.get("webUrl") or self.site_url,
            "parent_folder_path": relative_parent_path or "/",
            "file_metadata": file_metadata,
            "last_modified": last_modified,
            "file_type": name.rsplit(".", 1)[-1].lower() if "." in name else "",
        }
        
    async def get_file(self, file_url: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(file_url, headers=await self._headers())
            response.raise_for_status()
            file_content = response.content
            file_size = len(file_content)
            file_sha256 = httpx.utils.sha256(file_content).hexdigest()
            file_b64 = httpx.utils.base64.b64encode(file_content).decode("utf-8")

        return {
            "binary": file_content,
            "b64": file_b64,
            "size": file_size,
            "sha256": file_sha256,
        }

    async def get_site_document_libraries(self):
        async with httpx.AsyncClient(timeout=30) as client:
            return await self._get_document_libraries(client)

    async def get_site_documents(
        self, library_ids: list[str], modified_since: datetime | None = None
    ):
        library_ids = library_ids or []
        async with httpx.AsyncClient(timeout=1800) as client:
            site_id = await self._get_site_id(client)
            site = await self._get_json(
                client,
                f"{self.GRAPH_BASE_URL}/sites/{site_id}",
                params={"$select": "id,webUrl"},
            )
            libraries = await self._get_document_libraries(client)
            if library_ids:
                library_id_set = set(library_ids)
                libraries = [
                    library
                    for library in libraries
                    if library.get("id") in library_id_set
                ]

            documents_by_library = await asyncio.gather(
                *[
                    # self._get_library_documents(client, library, site, modified_since)
                    self._get_library_documents_from_list_items(client, library, site, modified_since)
                    for library in libraries
                ]
            )

        return [
            document
            for library_documents in documents_by_library
            for document in library_documents
        ]

    async def get_site_document(self, document_id: str, library_id: str):
        async with httpx.AsyncClient(timeout=30) as client:
            site_id = await self._get_site_id(client)
            site = await self._get_json(
                client,
                f"{self.GRAPH_BASE_URL}/sites/{site_id}",
                params={"$select": "id,webUrl"},
            )
            library, item = await asyncio.gather(
                self._get_json(
                    client,
                    f"{self.GRAPH_BASE_URL}/drives/{library_id}",
                    params={"$select": "id,name,webUrl,driveType"},
                ),
                self._get_json(
                    client,
                    f"{self.GRAPH_BASE_URL}/drives/{library_id}/items/{document_id}",
                    params={
                        "$select": (
                            "id,name,webUrl,file,folder,parentReference,size,"
                            "lastModifiedDateTime,createdDateTime,eTag,cTag,"
                            "createdBy,lastModifiedBy"
                        )
                    },
                ),
            )

        return self._format_document(item, library, site)

    async def _get_document_libraries(self, client: httpx.AsyncClient) -> list[dict]:
        site_id = await self._get_site_id(client)
        return await self._get_paged(
            client,
            f"{self.GRAPH_BASE_URL}/sites/{site_id}/drives",
            params={
                "$select": "id,name,webUrl,driveType",
                "$expand": "list($select=id,name)",
                "$top": 999,
            },
        )

    # TODO: update this to use delta instead (GET /drives/{drive-id}/root/delta)
    async def _get_library_documents(
        self,
        client: httpx.AsyncClient,
        library: dict,
        site: dict,
        modified_since: datetime | None,
    ) -> list[dict]:
        documents: list[dict] = []
        folders = ["root"]
        select = (
            "id,name,webUrl,file,folder,parentReference,size,lastModifiedDateTime,"
            "createdDateTime,eTag,cTag,createdBy,lastModifiedBy"
        )

        while folders:
            item_id = folders.pop()
            url = (
                f"{self.GRAPH_BASE_URL}/drives/{library['id']}/root/children"
                if item_id == "root"
                else (
                    f"{self.GRAPH_BASE_URL}/drives/{library['id']}"
                    f"/items/{item_id}/children"
                )
            )
            params = {"$select": select, "$top": 999}
            if modified_since is not None:
                params["$filter"] = (
                    f"lastModifiedDateTime ge {modified_since.isoformat()}"
                )
            children = await self._get_paged(client, url, params=params)

            for child in children:
                if "folder" in child:
                    folders.append(child["id"])
                    continue

                document = self._format_document(child, library, site)
                if not document:
                    continue

                last_modified = document.get("last_modified")
                if modified_since and last_modified:
                    modified_at = datetime.fromisoformat(
                        last_modified.replace("Z", "+00:00")
                    )
                    since = (
                        modified_since.replace(tzinfo=modified_at.tzinfo)
                        if modified_since.tzinfo is None
                        else modified_since
                    )
                    if modified_at <= since:
                        continue

                documents.append(document)

        return documents

    async def _get_library_documents_from_list_items(
        self,
        client: httpx.AsyncClient,
        library: dict,
        site: dict,
        modified_since: datetime | None,
    ) -> list[dict]:
        documents: list[dict] = []
        site_id = site["id"]
        library_list_id = library["list"]["id"]
        select = (
            "id,name"
            # "id,name,webUrl,file,folder,parentReference,size,"
            # "lastModifiedDateTime,createdDateTime,eTag,cTag,createdBy,lastModifiedBy"
        )

        url = f"{self.GRAPH_BASE_URL}/sites/{site_id}/lists/{library_list_id}/items"
        params = {"$select": select, "$top": 999999, "$expand": "driveItem"}
        if modified_since is not None:
            params["$filter"] = f"lastModifiedDateTime ge {modified_since.isoformat()}"

        list_items = await self._get_paged(client, url, params=params)
        for item in list_items:
            drive_item = item.get("driveItem")
            if not drive_item:
                continue

            document = self._format_document(drive_item, library, site)
            if not document:
                continue

            last_modified = document.get("last_modified")
            if modified_since and last_modified:
                modified_at = datetime.fromisoformat(
                    last_modified.replace("Z", "+00:00")
                )
                since = (
                    modified_since.replace(tzinfo=modified_at.tzinfo)
                    if modified_since.tzinfo is None
                    else modified_since
                )
                if modified_at <= since:
                    continue

            documents.append(document)

        return documents

    async def close(self):
        await self.credential.close()
