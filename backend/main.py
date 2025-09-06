import os, secrets
from typing import List, Optional
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .db import Base, engine, SessionLocal
from .models import Tenant, AppConfig
from .schemas import TenantCreate, TenantOut, ConfigCreate, ConfigOut, ConfigUpdate, ChatIn, ChatOut
from .security import encrypt, decrypt
from .kintone_client import KintoneClient
from .llm import answer_from_records

Base.metadata.create_all(bind=engine)

app = FastAPI()
origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",")]
app.add_middleware(CORSMiddleware, allow_origins=origins if origins != ["*"] else ["*"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

async def get_tenant(x_tenant_key: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not x_tenant_key:
        raise HTTPException(status_code=403, detail="X-Tenant-Key header required")
    t = db.query(Tenant).filter(Tenant.api_key == x_tenant_key).first()
    if not t: raise HTTPException(status_code=403, detail="Invalid X-Tenant-Key")
    return t

@app.get("/")
def root(): return {"ok": True, "service": "kintone-chatbot-saas"}

@app.post("/api/tenants", response_model=TenantOut)
def create_tenant(payload: TenantCreate, db: Session = Depends(get_db)):
    api_key = secrets.token_urlsafe(24)
    t = Tenant(name=payload.name, api_key=api_key); db.add(t); db.commit(); db.refresh(t)
    return TenantOut(api_key=t.api_key)

@app.get("/api/configs", response_model=List[ConfigOut])
def list_configs(tenant: Tenant = Depends(get_tenant), db: Session = Depends(get_db)):
    rows = db.query(AppConfig).filter(AppConfig.tenant_id == tenant.id).all()
    return [ConfigOut(id=r.id, name=r.name, domain=r.domain, app_id=r.app_id, target_fields=r.target_fields or []) for r in rows]

@app.post("/api/configs", response_model=ConfigOut)
def create_config(payload: ConfigCreate, tenant: Tenant = Depends(get_tenant), db: Session = Depends(get_db)):
    enc = encrypt(payload.api_token_plain)
    cfg = AppConfig(tenant_id=tenant.id, name=payload.name, domain=payload.domain, app_id=payload.app_id,
                    api_token_enc=enc, target_fields=payload.target_fields or [])
    db.add(cfg); db.commit(); db.refresh(cfg)
    return ConfigOut(id=cfg.id, name=cfg.name, domain=cfg.domain, app_id=cfg.app_id, target_fields=cfg.target_fields or [])

@app.put("/api/configs/{config_id}", response_model=ConfigOut)
def update_config(config_id: int, payload: ConfigUpdate, tenant: Tenant = Depends(get_tenant), db: Session = Depends(get_db)):
    cfg = db.query(AppConfig).filter(AppConfig.id == config_id, AppConfig.tenant_id == tenant.id).first()
    if not cfg: raise HTTPException(status_code=404, detail="Config not found")
    if payload.name is not None: cfg.name = payload.name
    if payload.domain is not None: cfg.domain = payload.domain
    if payload.app_id is not None: cfg.app_id = payload.app_id
    if payload.target_fields is not None: cfg.target_fields = payload.target_fields
    db.add(cfg); db.commit(); db.refresh(cfg)
    return ConfigOut(id=cfg.id, name=cfg.name, domain=cfg.domain, app_id=cfg.app_id, target_fields=cfg.target_fields or [])

@app.get("/api/kintone/fields")
async def kintone_fields(config_id: int, tenant: Tenant = Depends(get_tenant), db: Session = Depends(get_db)):
    cfg = db.query(AppConfig).filter(AppConfig.id == config_id, AppConfig.tenant_id == tenant.id).first()
    if not cfg: raise HTTPException(status_code=404, detail="Config not found")
    token = decrypt(cfg.api_token_enc)
    client = KintoneClient(cfg.domain, cfg.app_id, token)
    data = await client.fetch_fields()
    props = data.get("properties") or {}
    out = [{"code": c, "type": meta.get("type"), "label": meta.get("label")} for c, meta in (props.items() if isinstance(props, dict) else [])]
    return {"fields": out}

@app.post("/api/chat", response_model=ChatOut)
async def chat(payload: ChatIn, tenant: Tenant = Depends(get_tenant), db: Session = Depends(get_db)):
    cfg = db.query(AppConfig).filter(AppConfig.id == payload.config_id, AppConfig.tenant_id == tenant.id).first()
    if not cfg: raise HTTPException(status_code=404, detail="Config not found")
    if not cfg.target_fields: raise HTTPException(status_code=400, detail="target_fields is empty")
    like_field = cfg.target_fields[0]
    q = payload.query.replace('"', '\\"')
    kquery = f'{like_field} like "{q}"'
    token = decrypt(cfg.api_token_enc)
    client = KintoneClient(cfg.domain, cfg.app_id, token)
    data = await client.fetch_records(query=kquery, limit=50)
    records = data.get("records", [])
    sample = answer_from_records(records, cfg.target_fields or [like_field])
    total = int(data.get("totalCount") or len(records) or 0)
    return ChatOut(hits=total, sample=sample, query=payload.query, kintone_query=kquery)