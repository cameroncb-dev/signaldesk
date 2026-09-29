from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sys_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    short_description: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    urgency: Mapped[int] = mapped_column(Integer, default=2)
    impact: Mapped[int] = mapped_column(Integer, default=2)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    state: Mapped[str] = mapped_column(String(32), default="new")
    category: Mapped[str] = mapped_column(String(64), default="inquiry")
    subcategory: Mapped[str] = mapped_column(String(64), default="")
    assignment_group: Mapped[str] = mapped_column(String(128), default="")
    assigned_to: Mapped[str] = mapped_column(String(128), default="")
    cmdb_ci: Mapped[str] = mapped_column(String(64), default="")
    caller: Mapped[str] = mapped_column(String(128), default="")
    work_notes: Mapped[str] = mapped_column(Text, default="")
    close_notes: Mapped[str] = mapped_column(Text, default="")
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="ticket")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ci_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(64))
    region: Mapped[str] = mapped_column(String(64))
    owner_group: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="operational")
    details: Mapped[str] = mapped_column(Text, default="")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    model: Mapped[str] = mapped_column(String(64), default="heuristic")
    steps_json: Mapped[str] = mapped_column(Text, default="[]")
    recommendation_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ticket: Mapped[Ticket] = relationship(back_populates="agent_runs")
