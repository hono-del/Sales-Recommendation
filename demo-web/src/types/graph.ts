export type GraphNodeType =
  | "person"
  | "value"
  | "lifestyle"
  | "load"
  | "need"
  | "experience"
  | "feature"
  | "emotional_benefit"
  | "vehicle";

export type GraphNode = {
  id: string;
  type: GraphNodeType;
  label: string;
  subtype?: string;
  score?: number;
};

export type GraphEdge = {
  source: string;
  target: string;
  label?: string;
  highlighted?: boolean;
};

export type WhyPanelData = {
  values: { key?: string; label: string; percent: number }[];
  loads: string[];
  logic: string;
};

export type FilterFunnelStage = {
  label: string;
  count: number;
  filter_key?: string;
  excluded_reason?: string;
};

export type FilterFunnelData = {
  input: {
    family_size: number;
    budget_label: string;
    lifestyle: string;
    budget_min?: number;
    budget_max?: number;
  };
  stages: FilterFunnelStage[];
  exclusion_notes: string[];
};

export type ExperienceItem = {
  label: string;
  need_name?: string;
  need_group?: string;
  load_source?: string;
  value_axes?: string[];
  why_title: string;
  why_body: string;
};

export type FeatureCardItem = {
  name: string;
  feature_name?: string;
  headline: string;
  body: string;
  emotional_benefit: string;
  icon?: string;
};

export type VehicleDetail = {
  name: string;
  display_name?: string;
  score: number;
  reason: string;
  lifestyle_fit?: string;
  seating_capacity?: number;
  price_range?: string;
  fuel_type?: string;
  confidence_points?: string[];
};

export type ReasonTraceStep = {
  step: string;
  summary: string;
};

export type DecisionStyleInfo = {
  name: string;
  label: string;
  description?: string;
  confidence?: number;
  secondary_label?: string;
  is_mixed?: boolean;
};

export type StylePresentationVehicle = {
  rank: number;
  model: string;
  score_pct: number;
  price_range?: string;
  fuel_type?: string;
  seating_capacity?: number;
  appeal_points?: string[];
  reason?: string;
  highlights?: string[];
  gaps?: string[];
  verdict?: string;
};

export type StylePresentation = {
  ui_mode:
    | "comparison"
    | "sufficiency"
    | "trusted_pick"
    | "delegated_simple"
    | "experience"
    | "quick_pick";
  headline: string;
  subheadline?: string;
  style_name?: string;
  style_label?: string;
  style_description?: string;
  style_confidence?: number;
  style_secondary_label?: string;
  is_mixed?: boolean;
  why_rank1_title?: string;
  why_rank1_points?: string[];
  vehicles?: StylePresentationVehicle[];
  comparison_rows?: { label: string; values: string[] }[];
  checklist?: {
    title: string;
    met: boolean;
    items: string[];
    note?: string;
  }[];
  hero_vehicle?: Record<string, unknown>;
  alternatives_note?: string;
  proof_points?: string[];
  also_considered?: { model?: string; note?: string }[];
  scenes?: string[];
  optional_others?: string[];
  buyer_reviews?: BuyerReviewItem[];
  expert_voices?: ExpertVoiceItem[];
  review_count_label?: string;
  expert_count_label?: string;
};

export type BuyerReviewItem = {
  quote: string;
  meta: string;
  rating?: number;
  model?: string;
  source?: string;
};

export type ExpertVoiceItem = {
  source: string;
  title: string;
  quote: string;
  topic?: string;
  source_type?: string;
};

export type ThinkingProcessData = {
  filter_funnel?: FilterFunnelData;
  values: { key: string; label: string; percent: number }[];
  loads: string[];
  experiences: ExperienceItem[];
  features: FeatureCardItem[];
  vehicle: VehicleDetail;
  reason_trace?: { steps: ReasonTraceStep[] };
  decision_style?: DecisionStyleInfo;
  style_presentation?: StylePresentation;
};

export type GraphPathData = {
  demo_fallback?: boolean;
  nodes: GraphNode[];
  edges: GraphEdge[];
  why_panel: WhyPanelData;
  thinking_process: ThinkingProcessData;
};

/** force-graph 用 */
export type ForceNode = GraphNode & {
  appearPhase: number;
  x?: number;
  y?: number;
};

export type ForceLink = {
  source: string;
  target: string;
  label?: string;
  highlighted?: boolean;
  appearPhase: number;
};
