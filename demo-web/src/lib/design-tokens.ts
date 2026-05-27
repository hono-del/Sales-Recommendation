/** UI/UX 設計書に基づくデザイントークン */
export const colors = {
  navy: "#1A365D",
  navyLight: "#2D5A8E",
  gold: "#B8920C",
  bg: "#F5F7FA",
  surface: "#FFFFFF",
  border: "#E2E8F0",
  text: "#0D1B2A",
  textMuted: "#94A3B8",
  load: "#C53030",
  feature: "#2B6CB0",
  success: "#16A34A",
} as const;

export const layout = {
  maxWidth: "1280px",
  cardRadius: "6px",
  sectionGap: "48px",
} as const;

export const demoScreens = [
  { id: "SCR-01", path: "/demo/opening", label: "Opening" },
  { id: "SCR-02", path: "/demo/questions", label: "Questions" },
  { id: "SCR-03", path: "/demo/delegation", label: "Delegation" },
  { id: "SCR-04", path: "/demo/graph", label: "Graph" },
  { id: "SCR-05", path: "/demo/recommend", label: "Recommend" },
  { id: "SCR-06", path: "/demo/dealer", label: "Dealer" },
  { id: "SCR-07", path: "/demo/closing", label: "Closing" },
] as const;
