export type GraphNodeType =
  | "person"
  | "value"
  | "lifestyle"
  | "load"
  | "experience"
  | "feature"
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

export type GraphPathData = {
  demo_fallback?: boolean;
  nodes: GraphNode[];
  edges: GraphEdge[];
  why_panel: WhyPanelData;
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
