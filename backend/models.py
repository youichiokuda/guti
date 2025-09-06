from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    api_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    configs: Mapped[list["AppConfig"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")

class AppConfig(Base):
    __tablename__ = "app_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    domain: Mapped[str] = mapped_column(String(200), nullable=False)
    app_id: Mapped[int] = mapped_column(Integer, nullable=False)
    api_token_enc: Mapped[str] = mapped_column(String(1000), nullable=False)
    target_fields: Mapped[list[str]] = mapped_column(JSON, default=[])

    tenant: Mapped["Tenant"] = relationship(back_populates="configs")
