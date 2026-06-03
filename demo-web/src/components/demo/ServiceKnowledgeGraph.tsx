"use client";

type GraphNode = {
  id: string;
  label: string;
  type: "value" | "need" | "service";
  score?: number;
  x: number;
  y: number;
};

type GraphEdge = {
  from: string;
  to: string;
  strength?: number;
};

type Props = {
  values: Array<{ key: string; label: string; score: number }>;
  needs: string[];
  services: Array<{ id: string; title: string; matched_needs: string[] }>;
  needToValues?: Record<string, string[]>; // ニーズ → 価値観軸のマッピング
};

export function ServiceKnowledgeGraph({ values, needs, services, needToValues = {} }: Props) {
  // ノード配置
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];

  // レイヤー1: 価値観（左）
  const topValues = values.slice(0, 3); // 上位3つ
  topValues.forEach((value, idx) => {
    nodes.push({
      id: `value-${value.key}`,
      label: value.label,
      type: "value",
      score: value.score,
      x: 100,
      y: 150 + idx * 120,
    });
  });

  // レイヤー2: Need（中央）
  const displayNeeds = needs.slice(0, 5); // 上位5つ
  displayNeeds.forEach((need, idx) => {
    nodes.push({
      id: `need-${need}`,
      label: need.length > 15 ? need.substring(0, 15) + "..." : need,
      type: "need",
      x: 400,
      y: 100 + idx * 100,
    });
  });

  // レイヤー3: サービス（右）
  services.slice(0, 3).forEach((service, idx) => {
    nodes.push({
      id: `service-${service.id}`,
      label: service.title.length > 20 ? service.title.substring(0, 20) + "..." : service.title,
      type: "service",
      x: 700,
      y: 150 + idx * 150,
    });

    // エッジ: Need → Service（マッチ数に応じて強度を設定）
    const matchCount = service.matched_needs.length;
    service.matched_needs.forEach((needName, needIdx) => {
      const needNode = nodes.find((n) => n.id === `need-${needName}`);
      if (needNode) {
        // 最初のマッチを最も強く
        const strength = needIdx === 0 ? 0.9 : 0.5 / matchCount;
        edges.push({
          from: needNode.id,
          to: `service-${service.id}`,
          strength,
        });
      }
    });
  });

  // エッジ: 価値観 → Need（実際の回答ベースで接続）
  displayNeeds.forEach((need) => {
    // このニーズに関連する価値観軸を取得
    const relatedValueKeys = needToValues[need] || [];
    
    relatedValueKeys.forEach((valueKey) => {
      // この価値観軸が上位3つに含まれている場合のみエッジを作成
      const valueData = topValues.find(v => v.key === valueKey);
      if (valueData) {
        edges.push({
          from: `value-${valueKey}`,
          to: `need-${need}`,
          strength: valueData.score / 100, // 0-1の範囲に正規化
        });
      }
    });
  });

  // 最大強度を計算（赤色表示用）
  const maxStrength = Math.max(...edges.map(e => e.strength || 0));

  const svgWidth = 900;
  const svgHeight = 600;

  return (
    <div className="overflow-x-auto">
      <svg
        width={svgWidth}
        height={svgHeight}
        className="mx-auto"
        style={{ minWidth: `${svgWidth}px` }}
      >
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="10"
            refX="9"
            refY="3"
            orient="auto"
          >
            <polygon
              points="0 0, 10 3, 0 6"
              fill="#CBD5E1"
            />
          </marker>
        </defs>

        {/* エッジ（線） */}
        {edges.map((edge, idx) => {
          const fromNode = nodes.find((n) => n.id === edge.from);
          const toNode = nodes.find((n) => n.id === edge.to);
          if (!fromNode || !toNode) return null;

          const strength = edge.strength || 0.3;
          const isStrongest = strength === maxStrength && maxStrength > 0;
          
          // 線の太さ：強度に応じて1-5px
          const strokeWidth = Math.max(1, Math.min(5, strength * 6));
          
          // 線の色：最強は赤、それ以外は強度に応じたグレー
          const strokeColor = isStrongest ? "#EF4444" : "#CBD5E1";
          const opacity = isStrongest ? 0.9 : Math.max(0.2, strength * 0.7);

          return (
            <line
              key={`edge-${idx}`}
              x1={fromNode.x + 80}
              y1={fromNode.y}
              x2={toNode.x - 10}
              y2={toNode.y}
              stroke={strokeColor}
              strokeWidth={strokeWidth}
              opacity={opacity}
              markerEnd="url(#arrowhead)"
            />
          );
        })}

        {/* ノード */}
        {nodes.map((node) => {
          const colors = {
            value: { bg: "#DBEAFE", border: "#3B82F6", text: "#1E40AF" },
            need: { bg: "#FEF3C7", border: "#F59E0B", text: "#92400E" },
            service: { bg: "#E0E7FF", border: "#6366F1", text: "#3730A3" },
          };
          const color = colors[node.type];

          return (
            <g key={node.id}>
              {/* ノード背景 */}
              <rect
                x={node.x - 80}
                y={node.y - 20}
                width={160}
                height={40}
                rx={8}
                fill={color.bg}
                stroke={color.border}
                strokeWidth={2}
              />
              {/* ラベル */}
              <text
                x={node.x}
                y={node.y + 5}
                textAnchor="middle"
                fill={color.text}
                fontSize={12}
                fontWeight={500}
              >
                {node.label}
              </text>
              {/* スコア表示（価値観のみ） */}
              {node.score !== undefined && (
                <text
                  x={node.x}
                  y={node.y - 30}
                  textAnchor="middle"
                  fill={color.text}
                  fontSize={10}
                >
                  {Math.round(node.score)}%
                </text>
              )}
            </g>
          );
        })}

        {/* レイヤーラベル */}
        <text x={100} y={30} textAnchor="middle" fill="#64748B" fontSize={14} fontWeight={600}>
          価値観
        </text>
        <text x={400} y={30} textAnchor="middle" fill="#64748B" fontSize={14} fontWeight={600}>
          ニーズ
        </text>
        <text x={700} y={30} textAnchor="middle" fill="#64748B" fontSize={14} fontWeight={600}>
          推薦サービス
        </text>
      </svg>
    </div>
  );
}
