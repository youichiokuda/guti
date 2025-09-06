from typing import List, Optional
from pydantic import BaseModel

class TenantCreate(BaseModel):
    name: str
class TenantOut(BaseModel):
    api_key: str

class ConfigCreate(BaseModel):
    name: str
    domain: str
    app_id: int
    api_token_plain: str
    target_fields: List[str] = []

class ConfigUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    app_id: Optional[int] = None
    target_fields: Optional[List[str]] = None

class ConfigOut(BaseModel):
    id: int
    name: str
    domain: str
    app_id: int
    target_fields: List[str]

class ChatIn(BaseModel):
    query: str
    config_id: int

class ChatOut(BaseModel):
    hits: int
    sample: list
    query: str
    kintone_query: str