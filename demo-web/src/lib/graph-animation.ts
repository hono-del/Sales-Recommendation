import type { GraphEdge, GraphNode, ForceLink, ForceNode } from "@/types/graph";

export const PHASE_DURATION_MS = 800;
export const MAX_ANIMATION_PHASE = 6;

const TYPE_PHASE: Record<string, number> = {
  person: 0,
  value: 1,
  lifestyle: 1,
  experience: 2,
  need: 2,
  load: 2,
  feature: 3,
  vehicle: 4,
};

/** ノード出現フェーズを付与 */
export function enrichNodes(nodes: GraphNode[]): ForceNode[] {
  return nodes.map((n) => ({
    ...n,
    appearPhase: TYPE_PHASE[n.type] ?? 2,
  }));
}

/** エッジは両端ノードの max phase + 1、ハイライトは phase 6 */
export function enrichLinks(
  edges: GraphEdge[],
  nodes: ForceNode[],
): ForceLink[] {
  const phaseById = new Map(nodes.map((n) => [n.id, n.appearPhase]));
  const nodeById = new Map(nodes.map((n) => [n.id, n]));
  return edges.map((e) => {
    const src = phaseById.get(e.source) ?? 0;
    const tgt = phaseById.get(e.target) ?? 0;
    const base = Math.max(src, tgt) + 1;
    const targetsVehicle = nodeById.get(e.target)?.type === "vehicle";
    const highlighted = e.highlighted ?? targetsVehicle;
    return {
      ...e,
      highlighted,
      appearPhase: highlighted ? MAX_ANIMATION_PHASE : Math.min(base, 5),
    };
  });
}

export function visibleNodeIds(nodes: ForceNode[], phase: number): Set<string> {
  return new Set(nodes.filter((n) => n.appearPhase <= phase).map((n) => n.id));
}

export function visibleLinks(links: ForceLink[], phase: number): ForceLink[] {
  return links.filter((l) => l.appearPhase <= phase);
}

export const NODE_STYLE: Record<
  string,
  { fill: string; stroke: string; text: string; radius?: number; pill?: boolean }
> = {
  person: { fill: "#1A365D", stroke: "#1A365D", text: "#FFFFFF", radius: 22 },
  value: { fill: "#FFFFFF", stroke: "#1A365D", text: "#0D1B2A" },
  lifestyle: { fill: "#EEF2F7", stroke: "#94A3B8", text: "#0D1B2A", pill: true },
  load: { fill: "rgba(197, 48, 48, 0.15)", stroke: "#C53030", text: "#0D1B2A" },
  experience: { fill: "#EEF2F7", stroke: "#2B6CB0", text: "#0D1B2A" },
  need: { fill: "rgba(43, 108, 176, 0.18)", stroke: "#2B6CB0", text: "#0D1B2A" },
  feature: { fill: "rgba(43, 108, 176, 0.12)", stroke: "#2B6CB0", text: "#0D1B2A" },
  vehicle: { fill: "rgba(184, 146, 12, 0.2)", stroke: "#B8920C", text: "#0D1B2A" },
};

export const NARRATION_MESSAGES = [
  "あなたの価値観を分析しています…",
  "移動時のストレスや不安を検出しました。",
  "必要な体験と機能を特定しています…",
  "最適な車種を選定しています…",
];
