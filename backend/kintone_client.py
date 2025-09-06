import httpx

class KintoneClient:
    def __init__(self, domain: str, app_id: int, api_token: str):
        self.base = f"https://{domain}"
        self.app_id = app_id
        self.headers = {"X-Cybozu-API-Token": api_token, "Content-Type": "application/json"}

    async def fetch_records(self, query: str, limit: int = 50):
        url = f"{self.base}/k/v1/records.json"
        params = {"app": self.app_id, "query": query, "totalCount": "true", "limit": limit}
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.get(url, headers=self.headers, params=params)
            r.raise_for_status()
            return r.json()

    async def fetch_fields(self):
        url = f"{self.base}/k/v1/app/form/fields.json"
        params = {"app": self.app_id}
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.get(url, headers=self.headers, params=params)
            r.raise_for_status()
            return r.json()