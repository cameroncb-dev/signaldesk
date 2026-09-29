import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type { AgentRun, Health, Ticket } from "./types";

function Badge({ value, kind }: { value: string; kind?: string }) {
  const cls = kind ?? value.toLowerCase().replace(" ", "_");
  return <span className={`badge ${cls}`}>{value}</span>;
}

function priorityLabel(priority: number) {
  return `P${priority}`;
}

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [run, setRun] = useState<AgentRun | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const selected = useMemo(
    () => tickets.find((ticket) => ticket.id === selectedId) ?? null,
    [tickets, selectedId],
  );

  async function refresh() {
    const [nextTickets, nextHealth] = await Promise.all([api.tickets(), api.health()]);
    setTickets(nextTickets);
    setHealth(nextHealth);
    setSelectedId((current) => current ?? nextTickets[0]?.id ?? null);
  }

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setRun(null);
      return;
    }
    api
      .runs(selectedId)
      .then((runs) => setRun(runs[0] ?? null))
      .catch(() => setRun(null));
  }, [selectedId]);

  async function onRun() {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      setRun(await api.runAgent(selected.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Agent failed");
    } finally {
      setBusy(false);
    }
  }

  async function onApply() {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      const updated = await api.apply(selected.id);
      setTickets((current) => current.map((ticket) => (ticket.id === updated.id ? updated : ticket)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Apply failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="mark" />
          <div>
            <h1>SignalDesk</h1>
            <p>Agentic incident desk for connectivity operations</p>
          </div>
        </div>
        <div className="pills">
          <span className="pill">ServiceNow {health?.servicenow_mode ?? "…"}</span>
          <span className="pill">{health?.tickets ?? 0} incidents</span>
          <span className="pill">Azure-ready</span>
        </div>
      </header>

      <main className="desk">
        <section className="queue">
          <h2>Queue</h2>
          {tickets.map((ticket) => (
            <button
              key={ticket.id}
              className={`ticket-item ${ticket.id === selectedId ? "active" : ""}`}
              onClick={() => setSelectedId(ticket.id)}
            >
              <header>
                <strong>{ticket.number}</strong>
                <Badge value={priorityLabel(ticket.priority)} kind={`p${ticket.priority}`} />
              </header>
              <h3>{ticket.short_description}</h3>
              <p>
                {ticket.cmdb_ci || "No CI"} · {ticket.caller}
              </p>
            </button>
          ))}
        </section>

        <section className="detail">
          {selected ? (
            <>
              <h2>Incident</h2>
              <div className="row">
                <h3>{selected.short_description}</h3>
                <Badge value={selected.state} />
              </div>
              <p className="muted">
                {selected.number} · CI {selected.cmdb_ci || "n/a"} · opened{" "}
                {new Date(selected.opened_at).toLocaleString()}
              </p>
              <div className="actions">
                <button className="primary" disabled={busy} onClick={onRun}>
                  {busy ? "Working…" : "Run triage agent"}
                </button>
                <button className="ghost" disabled={busy || !run} onClick={onApply}>
                  Apply to ticket
                </button>
              </div>
              {error ? <p className="error">{error}</p> : null}
              <div className="panel">
                <p className="muted">Description</p>
                <p className="notes">{selected.description}</p>
              </div>
              <div className="panel">
                <div className="row">
                  <span>Assignment</span>
                  <strong>{selected.assignment_group || "Unassigned"}</strong>
                </div>
                <div className="row">
                  <span>Category</span>
                  <strong>
                    {selected.category}
                    {selected.subcategory ? ` / ${selected.subcategory}` : ""}
                  </strong>
                </div>
                {selected.work_notes ? (
                  <>
                    <p className="muted">Work notes</p>
                    <p className="notes">{selected.work_notes}</p>
                  </>
                ) : null}
              </div>
            </>
          ) : (
            <p className="muted">No incident selected.</p>
          )}
        </section>

        <section className="agent">
          <h2>Agent</h2>
          {run ? (
            <>
              <div className="panel">
                <div className="row">
                  <strong>Recommendation</strong>
                  <Badge value={run.model} kind="in_progress" />
                </div>
                <p>{run.recommendation.summary}</p>
                <p className="muted">
                  Route to {run.recommendation.assignment_group} · confidence{" "}
                  {Math.round(run.recommendation.confidence * 100)}%
                </p>
                <ul>
                  {run.recommendation.next_actions.map((action) => (
                    <li key={action}>{action}</li>
                  ))}
                </ul>
                <p className="muted">Customer update</p>
                <p>{run.recommendation.customer_update}</p>
              </div>
              <div className="panel">
                <p className="muted">Tool trace</p>
                {run.steps.map((step, index) => (
                  <div className="step" key={`${step.tool}-${index}`}>
                    <strong>{index + 1}. {step.tool}</strong>
                    <pre>{JSON.stringify(step.output, null, 2)}</pre>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="panel">
              <p>
                The agent gathers CMDB context, similar incidents, and assignment
                groups, then writes a recommendation. No Azure key needed for the
                local heuristic path.
              </p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
