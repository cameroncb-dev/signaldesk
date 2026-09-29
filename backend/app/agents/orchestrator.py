from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.agents.llm import synthesize_with_azure
from app.agents.tools import AgentToolbox
from app.config import settings
from app.models import AgentRun, Ticket
from app.schemas import AgentRunOut, AgentStep, Recommendation


KEYWORD_ROUTES = (
    (("fiber", "otdr", "span", "splice", "optical", "dwm"), "Fiber Operations", "network", "optical"),
    (("5g", "cell", "ran", "prb", "midband", "radio"), "Wireless RAN", "wireless", "capacity"),
    (("bgp", "router", "peering", "sip", "prefix"), "Core Network", "network", "routing"),
    (("api", "billing", "deploy", "apim", "5xx", "504"), "Digital Experience", "application", "regression"),
    (("servicenow", "table api", "cert", "itsm", "integration"), "IT Service Management", "integration", "auth"),
    (("azure", "landing", "identity"), "Cloud Platform", "application", "platform"),
)


def _priority(urgency: int, impact: int) -> int:
    return max(1, min(5, urgency + impact - 1))


def _heuristic(ticket: dict, asset: dict | None, similar: list[dict]) -> Recommendation:
    blob = f"{ticket.get('short_description', '')} {ticket.get('description', '')}".lower()
    group, category, subcategory = "IT Service Management", "inquiry", "general"
    for keywords, routed_group, routed_category, routed_sub in KEYWORD_ROUTES:
        if any(keyword in blob for keyword in keywords):
            group, category, subcategory = routed_group, routed_category, routed_sub
            break

    if asset and not asset.get("error"):
        group = asset.get("owner_group") or group
        if asset.get("kind") == "fiber_span":
            category, subcategory = "network", "fiber"
        elif asset.get("kind") == "cell_site":
            category, subcategory = "wireless", "ran"

    resolved = [row for row in similar if row.get("state") == "resolved"]
    if resolved and resolved[0].get("assignment_group"):
        group = resolved[0]["assignment_group"]

    priority = _priority(int(ticket.get("urgency", 2)), int(ticket.get("impact", 2)))
    ci = ticket.get("cmdb_ci") or (asset or {}).get("ci_id") or "unknown CI"
    actions = [
        f"Page {group} and attach CI {ci} to the incident.",
        "Post a customer-safe status with next update time.",
    ]
    if resolved:
        note = resolved[0].get("close_notes") or resolved[0].get("short_description")
        actions.append(f"Reuse close path from {resolved[0]['number']}: {note}")
    elif "fiber" in blob or "otdr" in blob:
        actions.append("Request field dispatch and a fresh OTDR trace at the loss marker.")
    elif "api" in blob:
        actions.append("Compare error budget vs. last good deploy and decide rollback vs. hotfix.")
    else:
        actions.append("Collect last-change and monitoring evidence before expanding the bridge.")

    customer = (
        f"We are investigating an incident affecting {ci}. "
        f"{group} owns the next technical step. "
        "We will update you as soon as impact or ETA changes."
    )
    summary = (
        f"{ticket.get('short_description')} looks like a {subcategory} issue on {ci}. "
        f"Recommended owner is {group}."
    )
    if asset and asset.get("details"):
        summary += f" CMDB notes: {asset['details']}"

    return Recommendation(
        category=category,
        subcategory=subcategory,
        priority=priority,
        assignment_group=group,
        summary=summary,
        customer_update=customer,
        next_actions=actions[:4],
        confidence=0.78 if resolved else 0.64,
        similar_ticket_numbers=[row["number"] for row in similar[:3]],
    )


def run_triage(db: Session, ticket: Ticket) -> AgentRunOut:
    tools = AgentToolbox(db)
    steps: list[AgentStep] = []

    def call(name: str, **kwargs) -> dict:
        output = tools.as_dispatch()[name](**kwargs)
        steps.append(AgentStep(tool=name, input=kwargs, output=output))
        return output

    ticket_payload = call("get_ticket", number=ticket.number)
    asset_payload = call("lookup_asset", ci_id=ticket.cmdb_ci) if ticket.cmdb_ci else {}
    if ticket.cmdb_ci and asset_payload.get("error"):
        asset_payload = call("search_cmdb", query=ticket.cmdb_ci)
    similar_payload = call("search_similar_incidents", number=ticket.number)
    groups_payload = call("list_assignment_groups")

    context = {
        "ticket": ticket_payload,
        "asset": asset_payload,
        "similar": similar_payload,
        "groups": groups_payload,
    }

    recommendation = None
    model = "heuristic"
    try:
        recommendation = synthesize_with_azure(ticket.number, context)
        if recommendation:
            model = settings.azure_openai_deployment
    except Exception as exc:  # demo must still complete if the model is down
        steps.append(
            AgentStep(
                tool="azure_openai_fallback",
                input={"reason": "synthesizer_error"},
                output={"error": str(exc)},
            )
        )

    if recommendation is None:
        recommendation = _heuristic(
            ticket_payload,
            asset_payload if not asset_payload.get("error") else None,
            similar_payload.get("matches", []),
        )

    run = AgentRun(
        ticket_id=ticket.id,
        status="completed",
        model=model,
        steps_json=json.dumps([step.model_dump() for step in steps]),
        recommendation_json=recommendation.model_dump_json(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return AgentRunOut(
        id=run.id,
        ticket_id=run.ticket_id,
        status=run.status,
        model=run.model,
        steps=steps,
        recommendation=recommendation,
        created_at=run.created_at,
    )


def run_to_out(run: AgentRun) -> AgentRunOut:
    return AgentRunOut(
        id=run.id,
        ticket_id=run.ticket_id,
        status=run.status,
        model=run.model,
        steps=[AgentStep.model_validate(item) for item in json.loads(run.steps_json)],
        recommendation=Recommendation.model_validate_json(run.recommendation_json),
        created_at=run.created_at,
    )
