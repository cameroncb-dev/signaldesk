from app.agents.orchestrator import _heuristic


def test_heuristic_routes_billing_to_digital():
    rec = _heuristic(
        {
            "short_description": "Billing API 5xx after deploy",
            "description": "APIM 504s on checkout",
            "urgency": 1,
            "impact": 1,
            "cmdb_ci": "API-BILL-PROD",
        },
        {"ci_id": "API-BILL-PROD", "owner_group": "Digital Experience", "kind": "application", "details": ""},
        [{"number": "INC0010019", "state": "resolved", "assignment_group": "Digital Experience", "close_notes": "Rollback"}],
    )
    assert rec.assignment_group == "Digital Experience"
    assert rec.priority == 1
    assert "INC0010019" in rec.similar_ticket_numbers
