import type { ProfileScores } from "@/lib/api-client";

/** API 失敗時のローカル fallback（config と同じ重みを簡略移植） */
const WEIGHTS: Record<string, Record<string, Partial<ProfileScores>>> = {
  q1_decision_style: {
    compare_thoroughly: { score_efficiency: 26, score_safety: 14 },
    good_enough: { score_efficiency: 24, score_family: 10 },
    trust_authority: { score_safety: 22, score_efficiency: 12 },
    ask_others: { score_family: 26, score_safety: 10 },
    intuition: { score_enjoyment: 24, score_adventure: 14 },
  },
  q2_stress_handling: {
    analyze_solve: { score_efficiency: 24, score_safety: 12 },
    accept_adapt: { score_family: 18, score_enjoyment: 12 },
    seek_support: { score_family: 26, score_safety: 10 },
    distance_refresh: { score_enjoyment: 22, score_adventure: 10 },
    challenge_growth: { score_adventure: 24, score_enjoyment: 12 },
  },
  q3_priority: {
    safety_security: { score_safety: 28, score_family: 10 },
    efficiency: { score_efficiency: 28, score_safety: 8 },
    family_time: { score_family: 28, score_safety: 10 },
    self_growth: { score_efficiency: 18, score_enjoyment: 12 },
    enjoyment: { score_enjoyment: 26, score_adventure: 14 },
  },
  q4_change: {
    cautious: { score_safety: 24, score_efficiency: 12 },
    practical: { score_efficiency: 22, score_safety: 10 },
    follow_trend: { score_enjoyment: 18, score_safety: 10 },
    ask_advice: { score_family: 22, score_safety: 12 },
    try_new: { score_adventure: 24, score_enjoyment: 14 },
  },
  q5_time_usage: {
    plan_optimize: { score_efficiency: 26, score_safety: 10 },
    balance: { score_efficiency: 18, score_family: 14, score_enjoyment: 10 },
    family_center: { score_family: 28, score_safety: 10 },
    learning_growth: { score_efficiency: 20, score_enjoyment: 12 },
    relax_enjoy: { score_enjoyment: 26, score_adventure: 12 },
  },
};

export function localProfileFromAnswer(
  questionId: string,
  answerKey: string,
  prev: ProfileScores | null,
): ProfileScores {
  const base: ProfileScores = prev ?? {
    score_safety: 20,
    score_family: 20,
    score_efficiency: 20,
    score_enjoyment: 20,
    score_adventure: 20,
  };
  const delta = WEIGHTS[questionId]?.[answerKey];
  if (!delta) return base;
  return {
    score_safety: Math.min(100, base.score_safety + (delta.score_safety ?? 0) * 0.3),
    score_family: Math.min(100, base.score_family + (delta.score_family ?? 0) * 0.3),
    score_efficiency: Math.min(100, base.score_efficiency + (delta.score_efficiency ?? 0) * 0.3),
    score_enjoyment: Math.min(100, base.score_enjoyment + (delta.score_enjoyment ?? 0) * 0.3),
    score_adventure: Math.min(100, base.score_adventure + (delta.score_adventure ?? 0) * 0.3),
  };
}
