# kintone-chatbot-saas

kintone の「ドメイン / アプリID / APIトークン / フィールドコード」を登録すると、そのアプリの内容に対して自然言語で問い合わせできる**外販SaaS向けのチャットボットAPI**です。Render (Docker) で即デプロイ可能。

## デプロイ（Render）

1. このリポジトリを GitHub に push
2. Render → New → Web Service → このリポジトリを選択（Runtime: Docker）
3. 環境変数を設定
   - `ENCRYPTION_KEY` … Fernet形式のキー（`openssl rand -base64 32` 推奨）
   - `ALLOWED_ORIGINS` … `*` またはフロントのドメイン
4. デプロイ後、`https://<service>.onrender.com` でトップページにアクセス

## API

- `POST /api/tenants` … テナント作成（戻り値 `api_key` を以後 `X-Tenant-Key` に設定）
- `GET /api/configs` … 設定一覧（ヘッダ `X-Tenant-Key`）
- `POST /api/configs` … 設定作成（kintone APIトークンは暗号化保存）
- `GET /api/kintone/fields?config_id=` … kintoneのフィールドコード&型を自動取得
- `POST /api/chat` … 先頭フィールドで LIKE 検索し、簡易結果を返却

## 使い方（最小）

```bash
# テナント作成
TENANT_KEY=$(curl -s -X POST https://<service>.onrender.com/api/tenants -H 'Content-Type: application/json' -d '{"name":"demo"}' | jq -r '.api_key')

# 設定作成
curl -s -X POST https://<service>.onrender.com/api/configs   -H 'Content-Type: application/json' -H "X-Tenant-Key: $TENANT_KEY"   -d '{"name":"案件","domain":"<sub>.cybozu.com","app_id":12345,"api_token_plain":"<TOKEN>","target_fields":["name","detail","assignee"]}'

# フィールド取得
curl -s "https://<service>.onrender.com/api/kintone/fields?config_id=1" -H "X-Tenant-Key: $TENANT_KEY" | jq .

# チャット
curl -s -X POST https://<service>.onrender.com/api/chat   -H 'Content-Type: application/json' -H "X-Tenant-Key: $TENANT_KEY"   -d '{"query":"中央","config_id":1}' | jq .
```

## 注意
- LIKE 検索は**テキスト型フィールド**でのみ機能します。`target_fields` の **先頭** をテキスト型にしてください。
- `ENCRYPTION_KEY` 未設定だと `/api/configs` で 500 になります。
