import styleWeights from "@/config/decision-style-weights.json";
import type { StoredAnswer } from "@/stores/demoStore";

export type DecisionStyleScores = Record<string, number>;

export type DecisionStyleResult = {
  name: string;
  label: string;
  description: string;
  confidence: number;
  secondary: string;
  secondaryLabel: string;
  scores: DecisionStyleScores;
  isMixed: boolean;
};

type StyleWeightsConfig = {
  decay_per_question: number;
  styles: string[];
  tie_break_order: string[];
  labels: Record<string, { label: string; description: string }>;
  answer_weights: Record<string, Record<string, Record<string, number>>>;
};

const CFG = styleWeights as StyleWeightsConfig;

function clamp(n: number): number {
  return Math.max(0, Math.min(100, Math.round(n * 10) / 10));
}

function answersByQid(answers: StoredAnswer[]): Record<string, string> {
  const map: Record<string, string> = {};
  for (const a of answers) {
    map[a.question_id] = a.answer_key;
  }
  return map;
}

function applyGuards(
  scores: DecisionStyleScores,
  byQid: Record<string, string>,
): DecisionStyleScores {
  const adjusted = { ...scores };
  const q5 = byQid.q5_ai ?? "";
  const q6 = byQid.q6_decision_process ?? "";
  const q7 = byQid.q7_info_preference ?? "";

  const delegatorOk =
    q6 === "ask_others" ||
    q7 === "people_pick" ||
    (q5 === "ai_decide" && q7 === "shortlist");

  const rerank = () =>
    Object.entries(adjusted).sort((a, b) => b[1] - a[1]);

  let ranked = rerank();
  if (ranked[0]?.[0] === "Delegator" && !delegatorOk) {
    adjusted.Delegator = Math.min(...Object.values(adjusted)) * 0.3;
    ranked = rerank();
  }

  ranked = rerank();
  if (ranked[0]?.[0] === "Impulsive" && q6 !== "quick_deal") {
    const second = ranked[1]?.[1] ?? 0;
    adjusted.Impulsive = Math.max(0, second - 1);
  }

  return adjusted;
}

/** API 失敗時のローカル DecisionStyle 推定（Python と同じ重み） */
export function computeDecisionStyleFromAnswers(
  answers: StoredAnswer[],
): DecisionStyleResult | null {
  const styles = CFG.styles;
  const raw: Record<string, number> = Object.fromEntries(styles.map((s) => [s, 0]));
  const sorted = [...answers].sort((a, b) => a.question_index - b.question_index);
  const decay = CFG.decay_per_question;

  for (let i = 0; i < sorted.length; i++) {
    const { question_id: qid, answer_key: key } = sorted[i];
    const factor = decay ** (sorted.length - 1 - i);
    const deltas = CFG.answer_weights[qid]?.[key] ?? {};
    for (const [style, delta] of Object.entries(deltas)) {
      if (style in raw) raw[style] += delta * factor;
    }
  }

  const peak = Math.max(...Object.values(raw), 0);
  if (peak <= 0) return null;

  let scores: DecisionStyleScores = Object.fromEntries(
    styles.map((s) => [s, clamp((raw[s] / peak) * 100)]),
  );

  scores = applyGuards(scores, answersByQid(sorted));

  const tieOrder = CFG.tie_break_order;
  const ranked = Object.entries(scores).sort((a, b) => {
    if (b[1] !== a[1]) return b[1] - a[1];
    return tieOrder.indexOf(a[0]) - tieOrder.indexOf(b[0]);
  });

  if (!ranked.length) return null;

  const primary = ranked[0][0];
  const secondary = ranked[1]?.[0] ?? primary;
  const margin = ranked[0][1] - (ranked[1]?.[1] ?? 0);
  const confidence = clamp(Math.min(100, margin * 2.5));
  const isMixed = confidence < 30;
  const meta = CFG.labels[primary] ?? { label: primary, description: "" };
  const secMeta = CFG.labels[secondary] ?? { label: secondary, description: "" };

  return {
    name: primary,
    label: meta.label,
    description: meta.description,
    confidence,
    secondary,
    secondaryLabel: secMeta.label,
    scores,
    isMixed,
  };
}

export function decisionStyleFromApiResponse(res: {
  decision_style?: string;
  decision_style_label?: string;
  decision_style_description?: string;
  decision_style_scores?: DecisionStyleScores;
  decision_style_confidence?: number;
  decision_style_secondary?: string;
  decision_style_secondary_label?: string;
  decision_style_is_mixed?: boolean;
}): DecisionStyleResult | null {
  if (!res.decision_style || !res.decision_style_scores) return null;
  return {
    name: res.decision_style,
    label: res.decision_style_label ?? res.decision_style,
    description: res.decision_style_description ?? "",
    confidence: res.decision_style_confidence ?? 0,
    secondary: res.decision_style_secondary ?? "",
    secondaryLabel: res.decision_style_secondary_label ?? "",
    scores: res.decision_style_scores,
    isMixed: res.decision_style_is_mixed ?? false,
  };
}
