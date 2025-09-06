from typing import List, Optional
from pydantic import BaseModel, Field

class TenantCreate(BaseModel):
    name: str

class TenantOut(BaseModel):
    id: int
    name: str
    api_key: str

class ConfigCreate(BaseModel):
    name: str
    domain: str
    app_id: int
    api_token_plain: str
    target_fields: List[str] = Field(default_factory=list)

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
