import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ProfileScores } from "@/lib/api-client";
import type { ExcludedModel, Recommendation } from "@/types/demo";

type DelegationLevel = "guide" | "co_pilot" | "auto";

export type StoredAnswer = {
  question_index: number;
  question_id: string;
  answer_key: string;
};

type DemoState = {
  sessionId: string | null;
  neo4jConnected: boolean | null;
  demoFallback: boolean;
  profile: ProfileScores | null;
  mappedNeeds: string[];
  answers: StoredAnswer[];
  answersCount: number;
  delegationLevel: DelegationLevel;
  recommendations: Recommendation[];
  excluded: ExcludedModel[];
  setSessionId: (id: string) => void;
  setNeo4jConnected: (v: boolean) => void;
  setDemoFallback: (v: boolean) => void;
  setProfile: (profile: ProfileScores, needs: string[]) => void;
  addAnswer: (answer: StoredAnswer) => void;
  setDelegationLevel: (level: DelegationLevel) => void;
  setRecommendations: (recs: Recommendation[], excluded: ExcludedModel[], fallback: boolean) => void;
  reset: () => void;
};

const initialState = {
  sessionId: null,
  neo4jConnected: null,
  demoFallback: false,
  profile: null,
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
      setNeo4jConnected: (v) => set({ neo4jConnected: v }),
      setDemoFallback: (v) => set({ demoFallback: v }),
      setProfile: (profile, mappedNeeds) => set({ profile, mappedNeeds }),
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
        profile: s.profile,
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
