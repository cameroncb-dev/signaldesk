from __future__ import annotations

import re
from collections.abc import Callable

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.adapters.servicenow import ticket_to_sn
from app.models import Asset, Ticket
from app.seed import ASSIGNMENT_GROUPS


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2}


class AgentToolbox:
    def __init__(self, db: Session):
        self.db = db

    def get_ticket(self, number: str) -> dict:
        ticket = self.db.query(Ticket).filter(Ticket.number == number).first()
        if not ticket:
            return {"error": f"ticket {number} not found"}
        return ticket_to_sn(ticket)

    def lookup_asset(self, ci_id: str) -> dict:
        asset = self.db.query(Asset).filter(Asset.ci_id == ci_id).first()
        if not asset:
            return {"error": f"CI {ci_id} not in CMDB"}
        return {
            "ci_id": asset.ci_id,
            "name": asset.name,
            "kind": asset.kind,
            "region": asset.region,
            "owner_group": asset.owner_group,
            "status": asset.status,
            "details": asset.details,
        }

    def search_similar_incidents(self, number: str, limit: int = 3) -> dict:
        ticket = self.db.query(Ticket).filter(Ticket.number == number).first()
        if not ticket:
            return {"matches": []}
        query_tokens = _tokens(f"{ticket.short_description} {ticket.description} {ticket.cmdb_ci}")
        scored: list[tuple[float, Ticket]] = []
        others = self.db.query(Ticket).filter(Ticket.number != number).all()
        for other in others:
            other_tokens = _tokens(f"{other.short_description} {other.description} {other.cmdb_ci}")
            if not query_tokens or not other_tokens:
                continue
            score = len(query_tokens & other_tokens) / len(query_tokens | other_tokens)
            if other.cmdb_ci and other.cmdb_ci == ticket.cmdb_ci:
                score += 0.25
            if other.state == "resolved":
                score += 0.05
            scored.append((score, other))
        scored.sort(key=lambda item: item[0], reverse=True)
        matches = [
            {
                "number": other.number,
                "short_description": other.short_description,
                "state": other.state,
                "assignment_group": other.assignment_group,
                "close_notes": other.close_notes,
                "score": round(score, 3),
            }
            for score, other in scored[:limit]
            if score > 0.05
        ]
        return {"matches": matches}

    def list_assignment_groups(self) -> dict:
        return {"groups": ASSIGNMENT_GROUPS}

    def search_cmdb(self, query: str) -> dict:
        like = f"%{query}%"
        rows = (
            self.db.query(Asset)
            .filter(
                or_(
                    Asset.ci_id.ilike(like),
                    Asset.name.ilike(like),
                    Asset.kind.ilike(like),
                    Asset.region.ilike(like),
                )
            )
            .limit(5)
            .all()
        )
        return {
            "results": [
                {
                    "ci_id": row.ci_id,
                    "name": row.name,
                    "kind": row.kind,
                    "owner_group": row.owner_group,
                    "status": row.status,
                }
                for row in rows
            ]
        }

    def as_dispatch(self) -> dict[str, Callable[..., dict]]:
        return {
            "get_ticket": self.get_ticket,
            "lookup_asset": self.lookup_asset,
            "search_similar_incidents": self.search_similar_incidents,
            "list_assignment_groups": self.list_assignment_groups,
            "search_cmdb": self.search_cmdb,
        }
