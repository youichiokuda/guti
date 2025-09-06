# kintone-chatbot-saas

        kintone のドメイン / アプリID / APIトークン / フィールドコードを設定して、kintoneアプリを LIKE 検索できる簡易チャットAPI＋GUI。

        ## ローカル
        ```bash
        python -m venv .venv && source .venv/bin/activate
        pip install -r requirements.txt
        export ENCRYPTION_KEY=$(python - <<'PY'
from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())
PY)
        uvicorn backend.main:app --reload
        ```

        ## Render
        1) GitHub に push → Render で Docker でデプロイ  
        2) 環境変数: `ENCRYPTION_KEY`（必須）, `ALLOWED_ORIGINS=*`, `DATABASE_URL=sqlite:////data/data.db`

        ## フロー
        1. / にアクセス → GUI で Tenant 作成（X-Tenant-Key 取得）
        2. Config 作成（ドメイン / AppID / APIトークンを登録）
        3. 「フィールド取得」で kintone から code/type/label を自動取得 → チェックして保存（PUT /api/configs/{id}）
        4. Chat: `target_fields[0]` を LIKE 対象にして検索

        **注意**: LIKE対象はテキスト型フィールドを先頭にしてください。