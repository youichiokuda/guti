from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    configs: Mapped[list["AppConfig"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")

class AppConfig(Base):
    __tablename__ = "app_configs"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_tenant_configname"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    app_id: Mapped[int] = mapped_column(Integer, nullable=False)
    api_token_enc: Mapped[str] = mapped_column(String, nullable=False)
    target_fields: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tenant: Mapped["Tenant"] = relationship(back_populates="configs")