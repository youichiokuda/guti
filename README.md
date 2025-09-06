# kintone-chatbot-saas

kintone アプリを対象に、自然言語でレコードを検索できるチャットボット SaaS。

## 機能

- テナントごとの API キー（`X-Tenant-Key`）発行
- kintone ドメイン / アプリID / APIトークン を登録し Config を作成
- フィールド自動取得 → GUI で選択して保存
- チャット入力すると `target_fields[0]` を LIKE 検索してヒットしたレコードを返す
- GUI（`static/index.html`）からブラウザのみで設定・利用可能

## 必要環境

- Python 3.11+
- FastAPI / SQLAlchemy / httpx
- DB: SQLite（Render では `/data` に永続化推奨）

## Render デプロイ

### 必須環境変数
- `ENCRYPTION_KEY` : Fernet 形式のキー  
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- `ALLOWED_ORIGINS` : CORS 許可ドメイン。テストは `*` で可
- `DATABASE_URL` : SQLite または Postgres  
  例: `sqlite:////data/data.db`

### 起動確認
Render デプロイ後に  
`https://<サービス名>.onrender.com`  
へアクセスし、次のレスポンスが返ればOK:
```json
{"ok": true, "service": "kintone-chatbot-saas"}
```

## API

### 1. テナント作成
```bash
curl -X POST https://<サービス>.onrender.com/api/tenants \
  -H 'Content-Type: application/json' \
  -d '{"name":"demo"}'
```

レスポンス例:
```json
{"id":1,"name":"demo","api_key":"<X-Tenant-Key>"}
```

### 2. Config 作成
```bash
curl -X POST https://<サービス>.onrender.com/api/configs \
  -H "X-Tenant-Key: <KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"sample",
    "domain":"xxxx.cybozu.com",
    "app_id":12345,
    "api_token_plain":"<KINTONE_API_TOKEN>",
    "target_fields":["name","detail","assignee"]
  }'
```

### 3. フィールド自動取得
```bash
curl "https://<サービス>.onrender.com/api/kintone/fields?config_id=1" \
  -H "X-Tenant-Key: <KEY>"
```

### 4. フィールド更新（PUT）
```bash
curl -X PUT https://<サービス>.onrender.com/api/configs/1 \
  -H "X-Tenant-Key: <KEY>" \
  -H "Content-Type: application/json" \
  -d '{"target_fields":["name","detail"]}'
```

### 5. チャット検索
```bash
curl -X POST https://<サービス>.onrender.com/api/chat \
  -H "X-Tenant-Key: <KEY>" \
  -H "Content-Type: application/json" \
  -d '{"query":"中央","config_id":1}'
```

## GUI 利用

ブラウザで `https://<サービス>.onrender.com` を開くと、  
以下のフローをGUIで操作可能です:

1. **Tenant 作成**（キー発行）
2. **Config 作成**
3. **フィールド自動取得 → チェックボックスで保存**
4. **チャット入力でレコード検索**

---
