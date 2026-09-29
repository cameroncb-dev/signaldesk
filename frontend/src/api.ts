import type { AgentRun, Health, Ticket } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/api/health"),
  tickets: () => request<Ticket[]>("/api/tickets"),
  runAgent: (id: number) => request<AgentRun>(`/api/tickets/${id}/agent-runs`, { method: "POST" }),
  runs: (id: number) => request<AgentRun[]>(`/api/tickets/${id}/agent-runs`),
  apply: (id: number) =>
    request<Ticket>(`/api/tickets/${id}/apply-recommendation`, {
      method: "POST",
      body: JSON.stringify({ add_work_notes: true, assign: true }),
    }),
};
