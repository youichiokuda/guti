import httpx
from typing import Dict, Any, List

class KintoneClient:
    def __init__(self, domain: str, app_id: int, api_token: str):
        self.base = f"https://{domain}"
        self.app_id = app_id
        self.headers = {
            "X-Cybozu-API-Token": api_token,
            "Content-Type": "application/json",
        }

    async def fetch_records(self, query: str | None, limit: int = 50) -> Dict[str, Any]:
        params = {"app": self.app_id, "totalCount": "true", "limit": limit}
        if query:
            params["query"] = query
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base}/k/v1/records.json", headers=self.headers, params=params)
            resp.raise_for_status()
            return resp.json()

    async def fetch_fields(self) -> Dict[str, Any]:
        params = {"app": self.app_id}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base}/k/v1/app/form/fields.json", headers=self.headers, params=params)
            resp.raise_for_status()
            return resp.json()
