import os
import secrets
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Path as FPath
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, Tenant, AppConfig
from .security import encrypt_api_token, decrypt_api_token
from .kintone_client import KintoneClient
from .llm import answer_from_records

# --- DB setup ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

# --- FastAPI app ---
app = FastAPI()

# static マウント
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).resolve().parent.parent / "static")),
    name="static",
)

# CORS
origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependencies ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_tenant(api_key: Optional[str] = Header(None, alias="X-Tenant-Key"), db: Session = Depends(get_db)) -> Tenant:
    if not api_key:
        raise HTTPException(status_code=403, detail="X-Tenant-Key header missing")
    tenant = db.query(Tenant).filter(Tenant.api_key == api_key).first()
    if not tenant:
        raise HTTPException(status_code=403, detail="Invalid tenant key")
    return tenant

# --- Schemas ---
class TenantCreate(BaseModel):
    name: str

class ConfigCreate(BaseModel):
    name: str
    domain: str
    app_id: int
    api_token_plain: str
    target_fields: List[str]

class ConfigUpdate(BaseModel):
    target_fields: List[str]

class ChatRequest(BaseModel):
    query: str
    config_id: int

# --- Utility ---
def _normalize_domain(raw: str) -> str:
    """https:// や /path を除去してホスト名のみに正規化"""
    d = (raw or "").strip()
    if d.startswith("http://"):
        d = d[len("http://"):]
    if d.startswith("https://"):
        d = d[len("https://"):]
    for sep in ["/", "?", "#"]:
        if sep in d:
            d = d.split(sep, 1)[0]
    return d

# --- Routes ---

# Root → GUI
@app.get("/", response_class=FileResponse)
def index():
    index_path = Path(__file__).resolve().parent.parent / "static" / "index.html"
    if not index_path.exists():
        return JSONResponse({"ok": True, "service": "kintone-chatbot-saas"})
    return FileResponse(str(index_path))

# Health check
@app.get("/health", response_class=JSONResponse)
def health():
    return {"ok": True, "service": "kintone-chatbot-saas"}

# Tenant 作成
@app.post("/api/tenants")
def create_tenant(body: TenantCreate, db: Session = Depends(get_db)):
    api_key = secrets.token_hex(16)
    tenant = Tenant(name=body.name, api_key=api_key)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return {"id": tenant.id, "name": tenant.name, "api_key": tenant.api_key}

# Config 作成
@app.post("/api/configs")
def create_config(body: ConfigCreate, tenant: Tenant = Depends(get_tenant), db: Session = Depends(get_db)):
    encrypted_token = encrypt_api_token(body.api_token_plain)
    norm_domain = _normalize_domain(body.domain)
    if not norm_domain or "." not in norm_domain:
        raise HTTPException(status_code=400, detail="Invalid domain. Use hostname only, e.g. 'example.cybozu.com'")
    config = AppConfig(
        tenant_id=tenant.id,
        name=body.name,
        domain=norm_domain,
        app_id=body.app_id,
        api_token=encrypted_token,
        target_fields=",".join(body.target_fields),
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return {
        "id": config.id,
        "name": config.name,
        "domain": config.domain,
        "app_id": config.app_id,
        "target_fields": config.target_fields.split(",") if config.target_fields else [],
    }

# Config 一覧
@app.get("/api/configs")
def list_configs(tenant: Tenant = Depends(get_tenant), db: Session = Depends(get_db)):
    configs = db.query(AppConfig).filter(AppConfig.tenant_id == tenant.id).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "domain": c.domain,
            "app_id": c.app_id,
            "target_fields": c.target_fields.split(",") if c.target_fields else [],
        }
        for c in configs
    ]

# Config 更新（target_fields）
@app.put("/api/configs/{config_id}")
def update_config(config_id: int, body: ConfigUpdate, tenant: Tenant = Depends(get_tenant), db: Session = Depends(get_db)):
    config = db.query(AppConfig).filter(AppConfig.id == config_id, AppConfig.tenant_id == tenant.id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    config.target_fields = ",".join(body.target_fields)
    db.commit()
    db.refresh(config)
    return {
        "id": config.id,
        "name": config.name,
        "domain": config.domain,
        "app_id": config.app_id,
        "target_fields": config.target_fields.split(",") if config.target_fields else [],
    }

# Config 削除
@app.delete("/api/configs/{config_id}")
def delete_config(config_id: int = FPath(...), tenant: Tenant = Depends(get_tenant), db: Session = Depends(get_db)):
    cfg = db.query(AppConfig).filter(AppConfig.id == config_id, AppConfig.tenant_id == tenant.id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    db.delete(cfg)
    db.commit()
    return {"ok": True}

# Kintone フィールド取得
@app.get("/api/kintone/fields")
async def get_kintone_fields(config_id: int, tenant: Tenant = Depends(get_tenant), db: Session = Depends(get_db)):
    config = db.query(AppConfig).filter(AppConfig.id == config_id, AppConfig.tenant_id == tenant.id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    api_token = decrypt_api_token(config.api_token)
    client = KintoneClient(config.domain, api_token, config.app_id)
    fields = await client.fetch_fields()
    return fields

# Chat
@app.post("/api/chat")
async def chat(req: ChatRequest, tenant: Tenant = Depends(get_tenant), db: Session = Depends(get_db)):
    config = db.query(AppConfig).filter(AppConfig.id == req.config_id, AppConfig.tenant_id == tenant.id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    api_token = decrypt_api_token(config.api_token)
    client = KintoneClient(config.domain, api_token, config.app_id)
    fields = config.target_fields.split(",") if config.target_fields else []
    if not fields:
        raise HTTPException(status_code=400, detail="No target_fields set")
    kquery = f'{fields[0]} like "{req.query}"'
    data = await client.fetch_records(query=kquery, limit=50)
    answer = answer_from_records(req.query, data.get("records", []))
    return {"query": req.query, "answer": answer, "records": data.get("records", [])}
