# backend/kintone_client.py

import httpx


class KintoneClient:
    def __init__(self, domain: str, api_token: str, app_id: int):
        self.domain = domain
        self.api_token = api_token
        self.app_id = app_id

        # ヘッダーは文字列のみ
        self.headers = {
            "X-Cybozu-API-Token": str(self.api_token),
            "Content-Type": "application/json",
        }

    async def fetch_records(self, query: str = "", limit: int = 50) -> dict:
        """
        レコードを取得
        """
        url = f"https://{self.domain}/k/v1/records.json"
        params = {
            "app": str(self.app_id),        # 数値は str() に
            "query": query,                 # 例: 'name like "foo"'
            "totalCount": "true",
            "limit": str(limit),
        }
        async with httpx.AsyncClient(timeout=60.0) as c:
            r = await c.get(url, headers=self.headers, params=params)
            r.raise_for_status()
            return r.json()

    async def fetch_fields(self) -> dict:
        """
        アプリのフィールド一覧を取得
        """
        url = f"https://{self.domain}/k/v1/app/form/fields.json"
        params = {"app": str(self.app_id)}   # app_id も必ず文字列
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.get(url, headers=self.headers, params=params)
            r.raise_for_status()
            data = r.json()
            properties = data.get("properties") or {}
            # 整形して返す
            fields = [
                {"code": code, **info}
                for code, info in properties.items()
            ]
            return {"fields": fields}
