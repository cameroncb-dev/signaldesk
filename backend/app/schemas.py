from datetime import datetime

from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    short_description: str
    description: str
    urgency: int = 2
    impact: int = 2
    cmdb_ci: str = ""
    caller: str = "ops-desk"


class TicketUpdate(BaseModel):
    state: str | None = None
    category: str | None = None
    subcategory: str | None = None
    assignment_group: str | None = None
    assigned_to: str | None = None
    priority: int | None = None
    work_notes: str | None = None
    close_notes: str | None = None


class TicketOut(BaseModel):
    id: int
    sys_id: str
    number: str
    short_description: str
    description: str
    urgency: int
    impact: int
    priority: int
    state: str
    category: str
    subcategory: str
    assignment_group: str
    assigned_to: str
    cmdb_ci: str
    caller: str
    work_notes: str
    close_notes: str
    opened_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssetOut(BaseModel):
    ci_id: str
    name: str
    kind: str
    region: str
    owner_group: str
    status: str
    details: str

    model_config = {"from_attributes": True}


class AgentStep(BaseModel):
    tool: str
    input: dict
    output: dict


class Recommendation(BaseModel):
    category: str
    subcategory: str
    priority: int
    assignment_group: str
    summary: str
    customer_update: str
    next_actions: list[str] = Field(default_factory=list)
    confidence: float
    similar_ticket_numbers: list[str] = Field(default_factory=list)


class AgentRunOut(BaseModel):
    id: int
    ticket_id: int
    status: str
    model: str
    steps: list[AgentStep]
    recommendation: Recommendation
    created_at: datetime


class ApplyRecommendationIn(BaseModel):
    add_work_notes: bool = True
    assign: bool = True
