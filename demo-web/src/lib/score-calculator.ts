import type { ProfileScores } from "@/lib/api-client";

/** API 失敗時のローカル fallback（config と同じ重みを簡略移植） */
const WEIGHTS: Record<string, Record<string, Partial<ProfileScores>>> = {
  q1_value: {
    safety: { score_safety: 28, score_family: 8 },
    enjoyment: { score_enjoyment: 28, score_adventure: 10 },
    family: { score_family: 28, score_safety: 12 },
    efficiency: { score_efficiency: 28, score_safety: 6 },
    status: { score_enjoyment: 14, score_adventure: 18, score_efficiency: 8 },
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
