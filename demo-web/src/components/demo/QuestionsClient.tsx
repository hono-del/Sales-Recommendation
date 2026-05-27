"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import { localProfileFromAnswer } from "@/lib/score-calculator";
import { useRequireSession } from "@/hooks/useRequireSession";
import { useDemoStore } from "@/stores/demoStore";
import type { Question, QuestionChoice } from "@/types/demo";
import { ProfileMap } from "./ProfileMap";
import { QuestionCard } from "./QuestionCard";

export function QuestionsClient() {
  const router = useRouter();
  const sessionId = useRequireSession();
  const profile = useDemoStore((s) => s.profile);
  const setProfile = useDemoStore((s) => s.setProfile);
  const addAnswer = useDemoStore((s) => s.addAnswer);

  const [questions, setQuestions] = useState<Question[]>([]);
  const [step, setStep] = useState(0);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [warn, setWarn] = useState<string | null>(null);

  useEffect(() => {
    api.getQuestions().then((data) => setQuestions(data.questions as Question[]));
  }, []);

  const current = questions[step];

  const submitAnswer = useCallback(
    async (choice: QuestionChoice) => {
      if (!sessionId || !current) return;
      setLoading(true);
      setWarn(null);
      const answerPayload = {
        question_index: current.index,
        question_id: current.id,
        answer_key: choice.key,
      };
      addAnswer(answerPayload);
      try {
        const res = await api.postAnswer(sessionId, answerPayload);
        setProfile(res.profile, res.mapped_needs);
      } catch {
        const fallback = localProfileFromAnswer(current.id, choice.key, profile);
        setProfile(fallback, []);
        setWarn("API に接続できません。回答は端末に保存済みです。推薦時に再送信します。");
      } finally {
        setLoading(false);
      }
    },
    [sessionId, current, profile, setProfile, addAnswer],
  );

  async function handleSelect(choice: QuestionChoice) {
    setSelectedKey(choice.key);
    await submitAnswer(choice);
  }

  function handleNext() {
    if (step < questions.length - 1) {
      setStep((s) => s + 1);
      setSelectedKey(null);
    } else {
      router.push("/demo/delegation");
    }
  }

  if (!current) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-text-muted">
        読み込み中…
      </div>
    );
  }

  return (
    <div className="mx-auto grid max-w-[1280px] gap-8 px-6 py-10 lg:grid-cols-5">
      <div className="lg:col-span-3">
        {warn && (
          <p className="mb-4 rounded-md border border-gold/40 bg-gold/10 px-4 py-2 text-sm text-navy">
            {warn}
          </p>
        )}
        <QuestionCard
          question={current}
          currentIndex={step + 1}
          total={questions.length}
          selectedKey={selectedKey}
          onSelect={handleSelect}
          onNext={handleNext}
          loading={loading}
        />
      </div>
      <div className="lg:col-span-2">
        <ProfileMap profile={profile} />
      </div>
    </div>
  );
}
