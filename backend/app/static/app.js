const state = { tickets: [], selectedId: null, run: null, busy: false };

const $ = (id) => document.getElementById(id);

async function request(path, init) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function badge(value, cls) {
  return `<span class="badge ${cls}">${value}</span>`;
}

function renderQueue() {
  $("queue").innerHTML = state.tickets
    .map(
      (ticket) => `
      <button class="ticket ${ticket.id === state.selectedId ? "active" : ""}" data-id="${ticket.id}">
        <div class="row">
          <strong>${ticket.number}</strong>
          ${badge(`P${ticket.priority}`, `p${ticket.priority}`)}
        </div>
        <h3>${ticket.short_description}</h3>
        <p>${ticket.cmdb_ci || "No CI"} · ${ticket.caller}</p>
      </button>`,
    )
    .join("");
  $("queue").querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => selectTicket(Number(button.dataset.id)));
  });
}

function selected() {
  return state.tickets.find((ticket) => ticket.id === state.selectedId) || null;
}

function renderDetail() {
  const ticket = selected();
  if (!ticket) {
    $("detail").innerHTML = `<h2>Incident</h2><p class="muted">No incident selected.</p>`;
    return;
  }
  $("detail").innerHTML = `
    <h2>Incident</h2>
    <div class="row">
      <h3>${ticket.short_description}</h3>
      ${badge(ticket.state, ticket.state)}
    </div>
    <p class="muted">${ticket.number} · CI ${ticket.cmdb_ci || "n/a"} · opened ${new Date(ticket.opened_at).toLocaleString()}</p>
    <div class="actions">
      <button class="primary" id="run" ${state.busy ? "disabled" : ""}>${state.busy ? "Working…" : "Run triage agent"}</button>
      <button class="ghost" id="apply" ${state.busy || !state.run ? "disabled" : ""}>Apply to ticket</button>
    </div>
    <p class="error" id="error"></p>
    <div class="panel">
      <p class="muted">Description</p>
      <p class="notes">${ticket.description}</p>
    </div>
    <div class="panel">
      <div class="row"><span>Assignment</span><strong>${ticket.assignment_group || "Unassigned"}</strong></div>
      <div class="row"><span>Category</span><strong>${ticket.category}${ticket.subcategory ? ` / ${ticket.subcategory}` : ""}</strong></div>
      ${ticket.work_notes ? `<p class="muted">Work notes</p><p class="notes">${ticket.work_notes}</p>` : ""}
    </div>
  `;
  $("run").addEventListener("click", onRun);
  $("apply").addEventListener("click", onApply);
}

function renderAgent() {
  if (!state.run) {
    $("agent").innerHTML = `
      <h2>Agent</h2>
      <div class="panel">
        <p>The agent gathers CMDB context, similar incidents, and assignment groups, then writes a recommendation. No Azure key is required for the local path.</p>
      </div>`;
    return;
  }
  const rec = state.run.recommendation;
  $("agent").innerHTML = `
    <h2>Agent</h2>
    <div class="panel">
      <div class="row">
        <strong>Recommendation</strong>
        ${badge(state.run.model, "in_progress")}
      </div>
      <p>${rec.summary}</p>
      <p class="muted">Route to ${rec.assignment_group} · confidence ${Math.round(rec.confidence * 100)}%</p>
      <ul>${rec.next_actions.map((action) => `<li>${action}</li>`).join("")}</ul>
      <p class="muted">Customer update</p>
      <p>${rec.customer_update}</p>
    </div>
    <div class="panel">
      <p class="muted">Tool trace</p>
      ${state.run.steps
        .map(
          (step, index) => `
        <div class="step">
          <strong>${index + 1}. ${step.tool}</strong>
          <pre>${JSON.stringify(step.output, null, 2)}</pre>
        </div>`,
        )
        .join("")}
    </div>
  `;
}

function setError(message) {
  const node = $("error");
  if (node) node.textContent = message;
}

async function selectTicket(id) {
  state.selectedId = id;
  const runs = await request(`/api/tickets/${id}/agent-runs`);
  state.run = runs[0] || null;
  renderQueue();
  renderDetail();
  renderAgent();
}

async function onRun() {
  const ticket = selected();
  if (!ticket) return;
  state.busy = true;
  renderDetail();
  try {
    state.run = await request(`/api/tickets/${ticket.id}/agent-runs`, { method: "POST" });
    setError("");
  } catch (err) {
    setError(err.message);
  } finally {
    state.busy = false;
    renderDetail();
    renderAgent();
  }
}

async function onApply() {
  const ticket = selected();
  if (!ticket) return;
  state.busy = true;
  renderDetail();
  try {
    const updated = await request(`/api/tickets/${ticket.id}/apply-recommendation`, {
      method: "POST",
      body: JSON.stringify({ add_work_notes: true, assign: true }),
    });
    state.tickets = state.tickets.map((row) => (row.id === updated.id ? updated : row));
    setError("");
  } catch (err) {
    setError(err.message);
  } finally {
    state.busy = false;
    renderQueue();
    renderDetail();
  }
}

async function boot() {
  const [tickets, health] = await Promise.all([request("/api/tickets"), request("/api/health")]);
  state.tickets = tickets;
  $("health-mode").textContent = `ServiceNow ${health.servicenow_mode}`;
  $("health-count").textContent = `${health.tickets} incidents`;
  await selectTicket(tickets[0]?.id);
}

boot();
