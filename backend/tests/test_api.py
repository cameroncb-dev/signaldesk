def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["tickets"] >= 1


def test_list_open_tickets(client):
    response = client.get("/api/tickets")
    assert response.status_code == 200
    numbers = {row["number"] for row in response.json()}
    assert "INC0010041" in numbers


def test_agent_run_and_apply(client):
    tickets = client.get("/api/tickets").json()
    fiber = next(row for row in tickets if row["number"] == "INC0010041")
    run = client.post(f"/api/tickets/{fiber['id']}/agent-runs")
    assert run.status_code == 200
    rec = run.json()["recommendation"]
    assert rec["assignment_group"] == "Fiber Operations"
    assert rec["similar_ticket_numbers"]
    tools = {step["tool"] for step in run.json()["steps"]}
    assert {"get_ticket", "lookup_asset", "search_similar_incidents", "list_assignment_groups"} <= tools

    applied = client.post(f"/api/tickets/{fiber['id']}/apply-recommendation", json={})
    assert applied.status_code == 200
    assert applied.json()["assignment_group"] == "Fiber Operations"
    assert applied.json()["state"] == "in_progress"
    assert "SignalDesk agent" in applied.json()["work_notes"]


def test_servicenow_table_api(client):
    listing = client.get("/api/now/table/incident")
    assert listing.status_code == 200
    first = listing.json()["result"][0]
    fetched = client.get(f"/api/now/table/incident/{first['sys_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["result"]["number"] == first["number"]
