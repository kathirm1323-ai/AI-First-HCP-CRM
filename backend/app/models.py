from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class HCP(Base):
    __tablename__ = "hcps"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    specialty: Mapped[str | None] = mapped_column(String(120))
    organization: Mapped[str | None] = mapped_column(String(180))
    interactions: Mapped[list["Interaction"]] = relationship(back_populates="hcp", cascade="all, delete-orphan")


class Interaction(Base):
    __tablename__ = "interactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    hcp_id: Mapped[int] = mapped_column(ForeignKey("hcps.id"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    interaction_type: Mapped[str] = mapped_column(String(20))
    products: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text)
    samples_distributed: Mapped[str | None] = mapped_column(Text)
    sentiment: Mapped[str | None] = mapped_column(String(30))
    follow_up_action: Mapped[str | None] = mapped_column(Text)
    compliance_flags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    hcp: Mapped[HCP] = relationship(back_populates="interactions")
    follow_ups: Mapped[list["FollowUp"]] = relationship(back_populates="interaction", cascade="all, delete-orphan")


class FollowUp(Base):
    __tablename__ = "follow_ups"
    id: Mapped[int] = mapped_column(primary_key=True)
    hcp_id: Mapped[int] = mapped_column(ForeignKey("hcps.id"), index=True)
    interaction_id: Mapped[int | None] = mapped_column(ForeignKey("interactions.id"))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    action: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")
    interaction: Mapped[Interaction | None] = relationship(back_populates="follow_ups")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    messages: Mapped[list] = mapped_column(JSON, default=list)
    pending_action: Mapped[dict | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
