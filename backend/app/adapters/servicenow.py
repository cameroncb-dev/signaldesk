"""ServiceNow-shaped incident adapter.

Default backend is the local SQL store using the same field names as the
ServiceNow Table API (`number`, `short_description`, `assignment_group`, ...).
If SERVICENOW_* env vars are set, writes/reads go to a real instance instead.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Ticket


SN_FIELDS = (
    "sys_id",
    "number",
    "short_description",
    "description",
    "urgency",
    "impact",
    "priority",
    "state",
    "category",
    "subcategory",
    "assignment_group",
    "assigned_to",
    "cmdb_ci",
    "caller",
    "work_notes",
    "close_notes",
    "opened_at",
)


def ticket_to_sn(ticket: Ticket) -> dict[str, Any]:
    return {
        "sys_id": ticket.sys_id,
        "number": ticket.number,
        "short_description": ticket.short_description,
        "description": ticket.description,
        "urgency": str(ticket.urgency),
        "impact": str(ticket.impact),
        "priority": str(ticket.priority),
        "state": ticket.state,
        "category": ticket.category,
        "subcategory": ticket.subcategory,
        "assignment_group": ticket.assignment_group,
        "assigned_to": ticket.assigned_to,
        "cmdb_ci": ticket.cmdb_ci,
        "caller_id": ticket.caller,
        "work_notes": ticket.work_notes,
        "close_notes": ticket.close_notes,
        "opened_at": ticket.opened_at.isoformat() + "Z",
        "sys_updated_on": ticket.updated_at.isoformat() + "Z",
    }


class ServiceNowAdapter:
    def __init__(self, db: Session):
        self.db = db

    @property
    def remote_enabled(self) -> bool:
        return bool(settings.servicenow_instance and settings.servicenow_user)

    def list_incidents(self) -> list[dict[str, Any]]:
        if self.remote_enabled:
            return self._remote("GET", "/api/now/table/incident")
        return [ticket_to_sn(t) for t in self.db.query(Ticket).order_by(Ticket.opened_at.desc())]

    def get_incident(self, sys_id: str) -> dict[str, Any] | None:
        if self.remote_enabled:
            rows = self._remote("GET", f"/api/now/table/incident/{sys_id}")
            return rows[0] if rows else None
        ticket = self.db.query(Ticket).filter(Ticket.sys_id == sys_id).first()
        return ticket_to_sn(ticket) if ticket else None

    def create_incident(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.remote_enabled:
            return self._remote("POST", "/api/now/table/incident", json=payload)[0]

        count = self.db.query(Ticket).count() + 1
        ticket = Ticket(
            sys_id=str(uuid4()),
            number=f"INC{10000 + count:07d}",
            short_description=payload.get("short_description", "New incident"),
            description=payload.get("description", ""),
            urgency=int(payload.get("urgency", 2)),
            impact=int(payload.get("impact", 2)),
            priority=max(1, min(5, int(payload.get("urgency", 2)) + int(payload.get("impact", 2)) - 1)),
            state="new",
            category=payload.get("category", "inquiry"),
            subcategory=payload.get("subcategory", ""),
            assignment_group=payload.get("assignment_group", ""),
            assigned_to=payload.get("assigned_to", ""),
            cmdb_ci=payload.get("cmdb_ci", ""),
            caller=payload.get("caller_id") or payload.get("caller", "ops-desk"),
            work_notes=payload.get("work_notes", ""),
            close_notes=payload.get("close_notes", ""),
        )
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket_to_sn(ticket)

    def update_incident(self, sys_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        if self.remote_enabled:
            rows = self._remote("PATCH", f"/api/now/table/incident/{sys_id}", json=payload)
            return rows[0] if rows else None

        ticket = self.db.query(Ticket).filter(Ticket.sys_id == sys_id).first()
        if not ticket:
            return None
        field_map = {
            "short_description": "short_description",
            "description": "description",
            "state": "state",
            "category": "category",
            "subcategory": "subcategory",
            "assignment_group": "assignment_group",
            "assigned_to": "assigned_to",
            "cmdb_ci": "cmdb_ci",
            "work_notes": "work_notes",
            "close_notes": "close_notes",
            "caller_id": "caller",
        }
        for incoming, attr in field_map.items():
            if incoming in payload:
                setattr(ticket, attr, payload[incoming])
        for numeric in ("urgency", "impact", "priority"):
            if numeric in payload:
                setattr(ticket, numeric, int(payload[numeric]))
        ticket.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(ticket)
        return ticket_to_sn(ticket)

    def _remote(self, method: str, path: str, json: dict | None = None) -> list[dict[str, Any]]:
        base = settings.servicenow_instance.rstrip("/")
        response = httpx.request(
            method,
            f"{base}{path}",
            auth=(settings.servicenow_user, settings.servicenow_password),
            json=json,
            timeout=20,
        )
        response.raise_for_status()
        result = response.json().get("result", [])
        if isinstance(result, dict):
            return [result]
        return result
