"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type { ForceGraphMethods, LinkObject, NodeObject } from "react-force-graph-2d";
import {
  MAX_ANIMATION_PHASE,
  NODE_STYLE,
  enrichLinks,
  enrichNodes,
  visibleLinks,
  visibleNodeIds,
} from "@/lib/graph-animation";
import type { GraphEdge, GraphNode } from "@/types/graph";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

type Props = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  animationPhase: number;
};

type LayoutNode = GraphNode & {
  appearPhase: number;
  fx?: number;
  fy?: number;
  x?: number;
  y?: number;
};

const COL_X: Record<string, number> = {
  person: -140,
  value: -50,
  lifestyle: 20,
  experience: 90,
  need: 120,
  load: 90,
  feature: 180,
  vehicle: 280,
};

function applyLayout(nodes: LayoutNode[]): LayoutNode[] {
  const buckets = new Map<string, LayoutNode[]>();
  for (const n of nodes) {
    const key = n.type;
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key)!.push(n);
  }
  const out: LayoutNode[] = [];
  for (const [, group] of buckets) {
    group.forEach((n, i) => {
      const col = COL_X[n.type] ?? 0;
      const spread = (i - (group.length - 1) / 2) * 56;
      out.push({ ...n, fx: col, fy: spread });
    });
  }
  return out;
}

function measureLabel(ctx: CanvasRenderingContext2D, text: string, fontSize: number) {
  ctx.font = `${fontSize}px "Segoe UI", system-ui, sans-serif`;
  return ctx.measureText(text).width;
}

function drawNode(
  node: LayoutNode,
  ctx: CanvasRenderingContext2D,
  globalScale: number,
  dashOffset: number,
) {
  const style = NODE_STYLE[node.type] ?? NODE_STYLE.value;
  const label = node.label;
  const sub = node.subtype;
  const fontSize = Math.max(10, 12 / globalScale);
  const padX = 10;
  const padY = 6;
  const textW = measureLabel(ctx, label, fontSize);
  const subW = sub ? measureLabel(ctx, sub, fontSize * 0.85) : 0;
  const w = Math.max(textW, subW) + padX * 2;
  const h = (sub ? fontSize * 2.4 : fontSize) + padY * 2;

  ctx.save();
  ctx.translate(node.x ?? 0, node.y ?? 0);

  if (node.type === "person") {
    const r = style.radius ?? 22;
    ctx.beginPath();
    ctx.arc(0, 0, r, 0, 2 * Math.PI);
    ctx.fillStyle = style.fill;
    ctx.fill();
    ctx.fillStyle = style.text;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.font = `600 ${fontSize}px system-ui`;
    ctx.fillText(label, 0, sub ? -fontSize * 0.35 : 0);
    if (sub) {
      ctx.font = `${fontSize * 0.8}px system-ui`;
      ctx.fillText(sub, 0, fontSize * 0.65);
    }
    ctx.restore();
    return;
  }

  const rx = style.pill ? h / 2 : 6;
  const x0 = -w / 2;
  const y0 = -h / 2;
  ctx.beginPath();
  ctx.roundRect(x0, y0, w, h, rx);
  ctx.fillStyle = style.fill;
  ctx.fill();
  ctx.strokeStyle = style.stroke;
  ctx.lineWidth = node.type === "vehicle" ? 2.5 / globalScale : 1.5 / globalScale;
  if (node.type === "vehicle" && dashOffset) {
    ctx.setLineDash([6 / globalScale, 4 / globalScale]);
    ctx.lineDashOffset = -dashOffset;
  }
  ctx.stroke();
  ctx.setLineDash([]);

  ctx.fillStyle = style.text;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = `500 ${fontSize}px system-ui`;
  ctx.fillText(label, 0, sub ? -fontSize * 0.2 : 0);
  if (sub) {
    ctx.font = `${fontSize * 0.75}px system-ui`;
    ctx.fillStyle = "#64748B";
    ctx.fillText(sub, 0, fontSize * 0.75);
  }
  if (node.score != null && node.type === "vehicle") {
    ctx.font = `600 ${fontSize * 0.85}px system-ui`;
    ctx.fillStyle = "#B8920C";
    ctx.fillText(`${Math.round(node.score * 100)}%`, 0, h / 2 - padY);
  }
  ctx.restore();
}

export function KnowledgeGraphView({ nodes, edges, animationPhase }: Props) {
  const fgRef = useRef<ForceGraphMethods<NodeObject, LinkObject> | undefined>(undefined);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 640, h: 420 });
  const [dashOffset, setDashOffset] = useState(0);
  const [entered, setEntered] = useState(false);

  const enriched = useMemo(() => enrichNodes(nodes), [nodes]);
  const allLinks = useMemo(() => enrichLinks(edges, enriched), [edges, enriched]);

  const visibleIds = useMemo(
    () => visibleNodeIds(enriched, animationPhase),
    [enriched, animationPhase],
  );
  const visibleNodes = useMemo(
    () => applyLayout(enriched.filter((n) => visibleIds.has(n.id))),
    [enriched, visibleIds],
  );
  const links = useMemo(
    () => visibleLinks(allLinks, animationPhase),
    [allLinks, animationPhase],
  );

  const graphData = useMemo(
    () => ({
      nodes: visibleNodes as NodeObject[],
      links: links.map((l) => ({
        source: l.source,
        target: l.target,
        label: l.label,
        highlighted: l.highlighted || l.appearPhase >= MAX_ANIMATION_PHASE,
      })),
    }),
    [visibleNodes, links],
  );

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      setSize({ w: el.clientWidth, h: el.clientHeight });
    });
    ro.observe(el);
    setSize({ w: el.clientWidth, h: el.clientHeight });
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const t = requestAnimationFrame(() => setEntered(true));
    return () => cancelAnimationFrame(t);
  }, []);

  useEffect(() => {
    if (animationPhase < MAX_ANIMATION_PHASE) return;
    let raf = 0;
    const tick = () => {
      setDashOffset((d) => (d + 1.2) % 24);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [animationPhase]);

  useEffect(() => {
    fgRef.current?.d3ReheatSimulation?.();
  }, [graphData]);

  const nodeCanvasObject = useCallback(
    (node: NodeObject, ctx: CanvasRenderingContext2D, globalScale: number) => {
      drawNode(node as LayoutNode, ctx, globalScale, dashOffset);
    },
    [dashOffset],
  );

  const linkCanvasObject = useCallback(
    (link: LinkObject, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const src = link.source as LayoutNode;
      const tgt = link.target as LayoutNode;
      if (src.x == null || src.y == null || tgt.x == null || tgt.y == null) return;
      const highlighted = Boolean((link as { highlighted?: boolean }).highlighted);
      ctx.beginPath();
      ctx.moveTo(src.x!, src.y!);
      ctx.lineTo(tgt.x!, tgt.y!);
      ctx.strokeStyle = highlighted ? "#B8920C" : "#CBD5E1";
      ctx.lineWidth = (highlighted ? 2.5 : 1.2) / globalScale;
      if (highlighted) {
        ctx.setLineDash([8 / globalScale, 5 / globalScale]);
        ctx.lineDashOffset = -dashOffset;
      }
      ctx.stroke();
      ctx.setLineDash([]);

      const label = (link as { label?: string }).label;
      if (label && highlighted) {
        const mx = (src.x! + tgt.x!) / 2;
        const my = (src.y! + tgt.y!) / 2;
        ctx.font = `${10 / globalScale}px system-ui`;
        ctx.fillStyle = "#64748B";
        ctx.textAlign = "center";
        ctx.fillText(label, mx, my - 6 / globalScale);
      }
    },
    [dashOffset],
  );

  const opacity = entered ? 1 : 0;

  return (
    <div
      ref={wrapRef}
      className="relative w-full overflow-hidden rounded-md border border-border bg-[#FAFBFC]"
      style={{ minHeight: 380, height: "min(52vh, 480px)", opacity, transition: "opacity 0.4s ease" }}
      aria-label="ナレッジグラフ"
    >
      {visibleNodes.length === 0 ? (
        <div className="flex h-full items-center justify-center text-sm text-text-muted">
          構築中…
        </div>
      ) : (
        <ForceGraph2D
          ref={fgRef}
          width={size.w}
          height={size.h}
          graphData={graphData}
          nodeId="id"
          nodeLabel=""
          linkLabel=""
          enableNodeDrag={false}
          enableZoomInteraction={animationPhase >= MAX_ANIMATION_PHASE}
          enablePanInteraction={animationPhase >= MAX_ANIMATION_PHASE}
          cooldownTicks={40}
          d3AlphaDecay={0.12}
          d3VelocityDecay={0.4}
          warmupTicks={30}
          nodeCanvasObjectMode={() => "replace"}
          nodeCanvasObject={nodeCanvasObject}
          linkCanvasObjectMode={() => "replace"}
          linkCanvasObject={linkCanvasObject}
          onEngineStop={() => fgRef.current?.zoomToFit(400, 48)}
        />
      )}
    </div>
  );
}
