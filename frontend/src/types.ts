export type Ticket = {
  id: number;
  sys_id: string;
  number: string;
  short_description: string;
  description: string;
  urgency: number;
  impact: number;
  priority: number;
  state: string;
  category: string;
  subcategory: string;
  assignment_group: string;
  assigned_to: string;
  cmdb_ci: string;
  caller: string;
  work_notes: string;
  close_notes: string;
  opened_at: string;
  updated_at: string;
};

export type AgentStep = {
  tool: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
};

export type Recommendation = {
  category: string;
  subcategory: string;
  priority: number;
  assignment_group: string;
  summary: string;
  customer_update: string;
  next_actions: string[];
  confidence: number;
  similar_ticket_numbers: string[];
};

export type AgentRun = {
  id: number;
  ticket_id: number;
  status: string;
  model: string;
  steps: AgentStep[];
  recommendation: Recommendation;
  created_at: string;
};

export type Health = {
  status: string;
  service: string;
  servicenow_mode: string;
  tickets: number;
};
