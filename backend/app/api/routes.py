from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.adapters.servicenow import ServiceNowAdapter, ticket_to_sn
from app.agents.orchestrator import run_to_out, run_triage
from app.db import get_db
from app.models import AgentRun, Asset, Ticket
from app.schemas import (
    AgentRunOut,
    ApplyRecommendationIn,
    AssetOut,
    TicketCreate,
    TicketOut,
    TicketUpdate,
)
from app.seed import ASSIGNMENT_GROUPS

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    adapter = ServiceNowAdapter(db)
    return {
        "status": "ok",
        "service": "signaldesk",
        "servicenow_mode": "remote" if adapter.remote_enabled else "local",
        "tickets": db.query(Ticket).count(),
    }


@router.get("/assignment-groups")
def assignment_groups() -> dict:
    return {"groups": ASSIGNMENT_GROUPS}


@router.get("/assets", response_model=list[AssetOut])
def list_assets(db: Session = Depends(get_db)) -> list[Asset]:
    return db.query(Asset).order_by(Asset.ci_id).all()


@router.get("/tickets", response_model=list[TicketOut])
def list_tickets(db: Session = Depends(get_db)) -> list[Ticket]:
    return db.query(Ticket).order_by(Ticket.opened_at.desc()).all()


@router.get("/tickets/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(404, "ticket not found")
    return ticket


@router.post("/tickets", response_model=TicketOut, status_code=201)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)) -> Ticket:
    created = ServiceNowAdapter(db).create_incident(payload.model_dump())
    ticket = db.query(Ticket).filter(Ticket.sys_id == created["sys_id"]).first()
    if not ticket:
        raise HTTPException(500, "ticket created but not readable")
    return ticket


@router.patch("/tickets/{ticket_id}", response_model=TicketOut)
def update_ticket(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db)) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(404, "ticket not found")
    updates = payload.model_dump(exclude_unset=True)
    if "work_notes" in updates and updates["work_notes"]:
        stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        existing = ticket.work_notes.strip()
        note = f"[{stamp}] {updates['work_notes']}"
        updates["work_notes"] = f"{existing}\n{note}".strip() if existing else note
    ServiceNowAdapter(db).update_incident(ticket.sys_id, updates)
    db.refresh(ticket)
    return ticket


@router.post("/tickets/{ticket_id}/agent-runs", response_model=AgentRunOut)
def create_agent_run(ticket_id: int, db: Session = Depends(get_db)) -> AgentRunOut:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(404, "ticket not found")
    return run_triage(db, ticket)


@router.get("/tickets/{ticket_id}/agent-runs", response_model=list[AgentRunOut])
def list_agent_runs(ticket_id: int, db: Session = Depends(get_db)) -> list[AgentRunOut]:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(404, "ticket not found")
    runs = (
        db.query(AgentRun)
        .filter(AgentRun.ticket_id == ticket_id)
        .order_by(AgentRun.created_at.desc())
        .all()
    )
    return [run_to_out(run) for run in runs]


@router.post("/tickets/{ticket_id}/apply-recommendation", response_model=TicketOut)
def apply_recommendation(
    ticket_id: int,
    payload: ApplyRecommendationIn,
    db: Session = Depends(get_db),
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(404, "ticket not found")
    run = (
        db.query(AgentRun)
        .filter(AgentRun.ticket_id == ticket_id)
        .order_by(AgentRun.created_at.desc())
        .first()
    )
    if not run:
        raise HTTPException(400, "run the agent before applying a recommendation")
    rec = run_to_out(run).recommendation
    updates: dict = {
        "category": rec.category,
        "subcategory": rec.subcategory,
        "priority": rec.priority,
        "state": "in_progress",
    }
    if payload.assign:
        updates["assignment_group"] = rec.assignment_group
    if payload.add_work_notes:
        stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        note = (
            f"[{stamp}] SignalDesk agent ({run.model}): {rec.summary} "
            f"Next: {'; '.join(rec.next_actions)}"
        )
        updates["work_notes"] = f"{ticket.work_notes}\n{note}".strip()
    ServiceNowAdapter(db).update_incident(ticket.sys_id, updates)
    db.refresh(ticket)
    return ticket


@router.get("/now/table/incident")
def now_list(db: Session = Depends(get_db)) -> dict:
    return {"result": ServiceNowAdapter(db).list_incidents()}


@router.get("/now/table/incident/{sys_id}")
def now_get(sys_id: str, db: Session = Depends(get_db)) -> dict:
    row = ServiceNowAdapter(db).get_incident(sys_id)
    if not row:
        raise HTTPException(404, "incident not found")
    return {"result": row}


@router.post("/now/table/incident")
def now_create(payload: dict, db: Session = Depends(get_db)) -> dict:
    return {"result": ServiceNowAdapter(db).create_incident(payload)}


@router.patch("/now/table/incident/{sys_id}")
def now_patch(sys_id: str, payload: dict, db: Session = Depends(get_db)) -> dict:
    row = ServiceNowAdapter(db).update_incident(sys_id, payload)
    if not row:
        raise HTTPException(404, "incident not found")
    return {"result": row}


@router.get("/tickets/{ticket_id}/servicenow")
def ticket_as_servicenow(ticket_id: int, db: Session = Depends(get_db)) -> dict:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(404, "ticket not found")
    return {"result": ticket_to_sn(ticket)}
