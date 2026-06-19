import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ProfileScores } from "@/lib/api-client";
import type { DecisionStyleResult } from "@/lib/decision-style-calculator";
import type { ExcludedModel, Recommendation } from "@/types/demo";

export type DelegationLevel = "guide" | "co_pilot" | "auto";

export type StoredAnswer = {
  question_index: number;
  question_id: string;
  answer_key: string;
};

type DemoState = {
  sessionId: string | null;
  recommendationType: "vehicle" | "service";
  neo4jConnected: boolean | null;
  demoFallback: boolean;
  profile: ProfileScores | null;
  decisionStyle: DecisionStyleResult | null;
  mappedNeeds: string[];
  answers: StoredAnswer[];
  answersCount: number;
  delegationLevel: DelegationLevel;
  recommendations: Recommendation[];
  excluded: ExcludedModel[];
  setSessionId: (id: string) => void;
  setRecommendationType: (type: "vehicle" | "service") => void;
  setNeo4jConnected: (v: boolean) => void;
  setDemoFallback: (v: boolean) => void;
  setProfile: (
    profile: ProfileScores,
    needs: string[],
    decisionStyle?: DecisionStyleResult | null,
  ) => void;
  addAnswer: (answer: StoredAnswer) => void;
  setDelegationLevel: (level: DelegationLevel) => void;
  setRecommendations: (recs: Recommendation[], excluded: ExcludedModel[], fallback: boolean) => void;
  reset: () => void;
};

const initialState = {
  sessionId: null,
  recommendationType: "vehicle" as "vehicle" | "service",
  neo4jConnected: null,
  demoFallback: false,
  profile: null,
  decisionStyle: null,
  mappedNeeds: [] as string[],
  answers: [] as StoredAnswer[],
  answersCount: 0,
  delegationLevel: "co_pilot" as DelegationLevel,
  recommendations: [] as Recommendation[],
  excluded: [] as ExcludedModel[],
};

export const useDemoStore = create<DemoState>()(
  persist(
    (set) => ({
      ...initialState,
      setSessionId: (id) => set({ sessionId: id }),
      setRecommendationType: (type) => set({ recommendationType: type }),
      setNeo4jConnected: (v) => set({ neo4jConnected: v }),
      setDemoFallback: (v) => set({ demoFallback: v }),
      setProfile: (profile, mappedNeeds, decisionStyle) =>
        set((state) => ({
          profile,
          mappedNeeds,
          decisionStyle: decisionStyle ?? state.decisionStyle,
        })),
      addAnswer: (answer) =>
        set((s) => {
          const answers = [
            ...s.answers.filter((a) => a.question_index !== answer.question_index),
            answer,
          ].sort((a, b) => a.question_index - b.question_index);
          return {
            answers,
            answersCount: answers.length,
          };
        }),
      setDelegationLevel: (delegationLevel) => set({ delegationLevel }),
      setRecommendations: (recommendations, excluded, demoFallback) =>
        set({ recommendations, excluded, demoFallback }),
      reset: () => set(initialState),
    }),
    {
      name: "decision-intelligence-demo",
      partialize: (s) => ({
        sessionId: s.sessionId,
        recommendationType: s.recommendationType,
        profile: s.profile,
        decisionStyle: s.decisionStyle,
        mappedNeeds: s.mappedNeeds,
        answers: s.answers,
        answersCount: s.answersCount,
        delegationLevel: s.delegationLevel,
        neo4jConnected: s.neo4jConnected,
        demoFallback: s.demoFallback,
        recommendations: s.recommendations,
        excluded: s.excluded,
      }),
    },
  ),
);
