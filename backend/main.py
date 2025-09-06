import os
import re
import secrets
from typing import List, Optional

from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .db import SessionLocal, engine, Base
from .models import Tenant, AppConfig
from .schemas import TenantCreate, TenantOut, ConfigCreate, ConfigOut, ChatIn, ChatOut
from .security import encrypt, decrypt
from .kintone_client import KintoneClient

Base.metadata.create_all(bind=engine)

app = FastAPI(title="kintone-chatbot-saas")

origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_tenant(x_tenant_key: Optional[str] = Header(None), db: Session = Depends(get_db)) -> Tenant:
    if not x_tenant_key:
        raise HTTPException(status_code=403, detail="X-Tenant-Key required")
    tenant = db.query(Tenant).filter(Tenant.api_key == x_tenant_key).first()
    if not tenant:
        raise HTTPException(status_code=403, detail="Invalid X-Tenant-Key")
    return tenant

@app.get("/")
def root():
    return {"ok": True, "service": "kintone-chatbot-saas"}

# Tenants
@app.post("/api/tenants", response_model=TenantOut)
def create_tenant(payload: TenantCreate, db: Session = Depends(get_db)):
    api_key = secrets.token_urlsafe(24)
    t = Tenant(name=payload.name, api_key=api_key)
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id, "name": t.name, "api_key": t.api_key}

# Configs
@app.get("/api/configs", response_model=List[ConfigOut])
def list_configs(tenant: Tenant = Depends(get_tenant), db: Session = Depends(get_db)):
    rows = db.query(AppConfig).filter(AppConfig.tenant_id == tenant.id).all()
    return [ConfigOut(id=r.id, name=r.name, domain=r.domain, app_id=r.app_id, target_fields=r.target_fields) for r in rows]

@app.post("/api/configs", response_model=ConfigOut)
def create_config(payload: ConfigCreate, tenant: Tenant = Depends(get_tenant), db: Session = Depends(get_db)):
    enc = encrypt(payload.api_token_plain)
    cfg = AppConfig(
        tenant_id=tenant.id,
        name=payload.name,
        domain=payload.domain,
        app_id=payload.app_id,
        api_token_enc=enc,
        target_fields=payload.target_fields or [],
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return ConfigOut(id=cfg.id, name=cfg.name, domain=cfg.domain, app_id=cfg.app_id, target_fields=cfg.target_fields)

# Kintone fields auto-fetch
@app.get("/api/kintone/fields")
async def kintone_fields(config_id: int, tenant: Tenant = Depends(get_tenant), db: Session = Depends(get_db)):
    cfg = db.query(AppConfig).filter(AppConfig.id == config_id, AppConfig.tenant_id == tenant.id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    token = decrypt(cfg.api_token_enc)
    client = KintoneClient(cfg.domain, cfg.app_id, token)
    data = await client.fetch_fields()
    # Return simplified list: code & type & label
    fields = []
    for code, meta in data.get("properties", {}).items():
        fields.append({"code": code, "type": meta.get("type"), "label": meta.get("label")})
    return {"fields": fields}

# Simple chat -> Kintone query
@app.post("/api/chat", response_model=ChatOut)
async def chat(body: ChatIn, tenant: Tenant = Depends(get_tenant), db: Session = Depends(get_db)):
    cfg = db.query(AppConfig).filter(AppConfig.id == body.config_id, AppConfig.tenant_id == tenant.id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    if not cfg.target_fields:
        raise HTTPException(status_code=400, detail="target_fields is empty")
    first_field = cfg.target_fields[0]
    q = body.query.strip().replace('"', '\"')
    # Kintone LIKE only works for text fields.
    kquery = f'{first_field} like "{q}"'
    token = decrypt(cfg.api_token_enc)
    client = KintoneClient(cfg.domain, cfg.app_id, token)
    data = await client.fetch_records(query=kquery, limit=50)
    records = data.get("records", [])
    # Reduce to selected fields for response
    sample = []
    for r in records[:5]:
        row = {}
        for f in cfg.target_fields:
            if f in r and isinstance(r[f], dict) and "value" in r[f]:
                row[f] = r[f]["value"]
        sample.append(row)
    return ChatOut(hits=len(records), sample=sample)
