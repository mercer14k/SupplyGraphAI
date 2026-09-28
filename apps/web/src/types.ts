export type NodeKind =
  | "supplier"
  | "site"
  | "component"
  | "product"
  | "facility"
  | "port"
  | "route"
  | "customer";
export interface Provenance {
  id: string;
  source_id: string;
  ingested_at: string;
  validation_status: string;
  lineage: Record<string, unknown>;
}
export interface GraphNode extends Provenance {
  kind: NodeKind;
  name: string;
  country: string;
  tier: number;
  daily_demand: number;
  unit_value: number;
  latitude: number;
  longitude: number;
}
export interface GraphEdge extends Provenance {
  source: string;
  target: string;
  kind: string;
  group: string;
  approved: boolean;
  capacity: number;
  required_capacity: number;
  lead_time_days: number;
  quantity: number;
}
export interface GraphData {
  snapshot_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  total_nodes: number;
  truncated: boolean;
}
export interface Critical {
  node_id: string;
  name: string;
  kind: string;
  betweenness: number;
  out_degree: number;
  degree_centrality: number;
  evidence_ids: string[];
}
export interface Overview {
  snapshot_id: string;
  nodes: number;
  edges: number;
  counts: Record<string, number>;
  single_source_groups: number;
  inventory_records: number;
  supplier_tiers: number;
  countries: number;
  critical: Critical[];
  effective_at: string;
  source_id: string;
}
export interface Snapshot {
  id: string;
  effective_at: string;
  source_id: string;
  digest: string;
  seed: number;
}
export interface Impact {
  node_id: string;
  name: string;
  kind: NodeKind;
  shortage_day: number;
  lost_units: number;
  exposure_value: number;
  path: string[];
  evidence_ids: string[];
}
export interface Scenario {
  snapshot_id: string;
  disrupted_ids: string[];
  duration_days: number;
  candidate_count: number;
  affected_count: number;
  affected_products: number;
  lost_product_units: number;
  product_exposure_value: number;
  impacts: Impact[];
  alternates: {
    target_id: string;
    source_id: string;
    group: string;
    evidence_ids: string[];
  }[];
  evidence_ids: string[];
  assumptions: string[];
  algorithm_version: string;
}
export interface QueryResult {
  status: "answered" | "abstained";
  mode: string;
  claims: { text: string; evidence_ids: string[]; origin: string }[];
  reason: string | null;
  evidence_ids: string[];
  telemetry: Record<string, unknown>;
}
export interface Report {
  id: string;
  valid: boolean;
  filename: string;
  created_at: string;
  node_count: number;
  edge_count: number;
  errors: {
    code: string;
    message: string;
    record_id?: string;
    location?: string;
  }[];
  warnings: { code: string; message: string; record_id?: string }[];
}
export interface Config {
  ai_enabled: boolean;
  runtime: string;
  model: string;
  mutation_enabled: boolean;
  demo: boolean;
}
export interface NodePage {
  items: GraphNode[];
  total: number;
  limit: number;
  offset: number;
}
