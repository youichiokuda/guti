# backend/kintone_client.py
import httpx


class KintoneClient:
    """
    kintone API クライアント（最低限）
      - fetch_records: レコード検索
      - fetch_fields : まず form/fields API を試し、ダメなら records から推測
    """

    def __init__(self, domain: str, app_id: int, api_token: str):
        self.domain = domain
        self.app_id = app_id
        # httpx はヘッダ値が str 必須なので明示的に文字列化しない値は入れない
        self.headers = {
            "X-Cybozu-API-Token": api_token,
            "Content-Type": "application/json",
        }

    async def fetch_records(self, query: str = "", limit: int = 100):
        url = f"https://{self.domain}/k/v1/records.json"
        params = {"app": str(self.app_id), "totalCount": "true", "limit": str(limit)}
        if query:
            params["query"] = query

        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.get(url, headers=self.headers, params=params)
            if r.status_code >= 400:
                # そのまま本文を返すとデバッグが容易
                return {
                    "error": True,
                    "status": r.status_code,
                    "url": str(r.request.url),
                    "body": r.text,
                }
            return r.json()

    async def fetch_fields(self):
        """
        1) 設定API (/k/v1/app/form/fields.json) を試す
        2) 4xx 等で失敗したら、records 1件取得し、キーから field code を推測
        """
        # 1) 設定API（最も正確）
        form_url = f"https://{self.domain}/k/v1/app/form/fields.json"
        form_params = {"app": str(self.app_id)}

        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.get(form_url, headers=self.headers, params=form_params)
            if r.status_code < 400:
                data = r.json()
                props = data.get("properties", {}) or {}
                codes = sorted(props.keys())
                return {"source": "form_api", "field_codes": codes}

            # 2) フォールバック：records を 1 件取得して推測
            rec_url = f"https://{self.domain}/k/v1/records.json"
            rec_params = {"app": str(self.app_id), "limit": "1", "totalCount": "false"}
            r2 = await c.get(rec_url, headers=self.headers, params=rec_params)
            if r2.status_code >= 400:
                return {
                    "error": True,
                    "status": r2.status_code,
                    "form_api_status": r.status_code,
                    "form_api_body": r.text,
                    "records_body": r2.text,
                    "message": "Cannot fetch field codes from form API nor records.",
                }

            recs = r2.json().get("records", []) or []
            if not recs:
                return {"source": "records_fallback", "field_codes": []}

            # 1レコードのキーを候補とする
            codes = sorted(list(recs[0].keys()))
            return {"source": "records_fallback", "field_codes": codes}
