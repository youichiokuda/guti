# backend/kintone_client.py
from __future__ import annotations
import httpx
from typing import List, Optional, Dict, Any

class KintoneClient:
    def __init__(self, domain: str, app_id: int | str, api_token: str):
        self.base_url = f"https://{domain}"
        # app_id は数値として内部で保持しつつ、送信時は str にします
        self.app_id = int(app_id)
        # すべて str にキャストしておく（ヘッダーは文字列のみ）
        self.headers: Dict[str, str] = {
            "X-Cybozu-API-Token": str(api_token or ""),  # 空でも str
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }

    async def fetch_fields(self) -> List[str]:
        """
        kintone フィールド一覧（フィールドコード）取得
        GET /k/v1/app/form/fields.json?app={app_id}
        """
        url = f"{self.base_url}/k/v1/app/form/fields.json"
        params = {"app": str(self.app_id)}
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.get(url, headers=self.headers, params=params)
            r.raise_for_status()
            data: Dict[str, Any] = r.json()
            props: Dict[str, Any] = data.get("properties", {})
            # 各プロパティの code を抽出
            codes = []
            for v in props.values():
                code = v.get("code")
                if isinstance(code, str) and code:
                    codes.append(code)
            return codes

    async def fetch_records(
        self,
        query: str = "",
        limit: int = 50,
        offset: int = 0,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        kintone レコード取得
        GET /k/v1/records.json?app={app_id}&query=...&limit=...&offset=...&totalCount=true
        """
        url = f"{self.base_url}/k/v1/records.json"
        params: Dict[str, str] = {
            "app": str(self.app_id),
            "totalCount": "true",
        }
        if query:
            params["query"] = query
        if limit is not None:
            params["limit"] = str(int(limit))
        if offset:
            params["offset"] = str(int(offset))

        # fields[] は GET の場合は繰り返しクエリとして渡す形を推奨（httpx は自動で展開）
        req_params = list(params.items())
        if fields:
            for f in fields:
                req_params.append(("fields[]", str(f)))

        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.get(url, headers=self.headers, params=req_params)
            r.raise_for_status()
            return r.json()
