# backend/models.py
from __future__ import annotations
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, ForeignKey, DateTime, Text, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AppConfig(Base):
    __tablename__ = "app_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # kintone 接続情報
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    app_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # ← これが今回必要：暗号化済みトークンを保存するカラム
    api_token: Mapped[str] = mapped_column(Text, nullable=False)

    # カンマ区切りで保持（例: "name,detail,assignee"）
    target_fields: Mapped[Optional[str]] = mapped_column(Text, default="", nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# よく使う検索に備えて index 追加例（任意）
Index("idx_app_configs_tenant", AppConfig.tenant_id)
Index("idx_app_configs_app", AppConfig.app_id)
