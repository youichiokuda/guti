# backend/kintone_client.py
import httpx


class KintoneClient:
    def __init__(self, domain: str, api_token: str, app_id: int):
        self.domain = domain
        self.api_token = api_token
        self.app_id = app_id
        self.headers = {
            "X-Cybozu-API-Token": str(self.api_token),
            "Content-Type": "application/json",
        }

    async def fetch_records(self, query: str = "", limit: int = 50) -> dict:
        url = f"https://{self.domain}/k/v1/records.json"
        params = {
            "app": str(self.app_id),
            "totalCount": "true",
            "limit": str(limit),
        }
        if query:
            params["query"] = query
        async with httpx.AsyncClient(timeout=60.0) as c:
            r = await c.get(url, headers=self.headers, params=params)
            r.raise_for_status()
            return r.json()

    async def fetch_fields(self) -> dict:
        """
        フィールド一覧を records.json（APIトークン対応）から推定して返す。
        アプリ設定API（app/form/fields.json）はAPIトークン非対応のため使用しない。
        """
        # 1件だけ取得してキーを読む
        data = await self.fetch_records(limit=1)
        records = data.get("records") or []
        if not records:
            # レコードが無い場合は最低限 app_id だけ返す
            return {"fields": []}

        sample = records[0]  # dict
        fields = []
        for code, val in sample.items():
            # kintoneのレコードJSONは {"フィールドコード": {"type": "...", "value": ...}} の形
            ftype = (val or {}).get("type")
            fields.append({"code": code, "type": ftype})
        return {"fields": fields}
