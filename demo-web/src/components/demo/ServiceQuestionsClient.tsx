"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useRequireSession } from "@/hooks/useRequireSession";
import { useDemoStore } from "@/stores/demoStore";
import { api } from "@/lib/api-client";
import type { Question, QuestionChoice } from "@/types/demo";
import { PrimaryButton } from "./PrimaryButton";
import { DecisionStylePanel } from "./DecisionStylePanel";
import { ProfileMap } from "./ProfileMap";

export function ServiceQuestionsClient() {
  const router = useRouter();
  const sessionId = useRequireSession();
  const addAnswer = useDemoStore((s) => s.addAnswer);
  const setProfile = useDemoStore((s) => s.setProfile);

  const [questions, setQuestions] = useState<Question[]>([]);
  const [step, setStep] = useState(0);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [profile, setLocalProfile] = useState<Record<string, number>>({});
  const [decisionStyle, setDecisionStyle] = useState<{
    name: string;
    label: string;
    description: string;
  } | null>(null);

  useEffect(() => {
    // サービスレコメンド用の質問を取得
    api.getServiceQuestions().then((data) => setQuestions(data.questions as Question[]));
  }, []);

  const current = questions[step];

  const submitAnswer = useCallback(
    async (choice: QuestionChoice) => {
      if (!sessionId || !current) return;
      setLoading(true);
      const answerPayload = {
        question_index: current.index,
        question_id: current.id,
        answer_key: choice.key,
      };
      try {
        // APIに回答を送信
        const res = await api.postAnswer(sessionId, answerPayload);
        // ローカルストアにも保存
        addAnswer(answerPayload);
        
        // プロファイルとDecisionStyleを更新
        if (res.profile) {
          setLocalProfile(res.profile);
          setProfile(res.profile, res.mapped_needs || [], {
            name: res.decision_style || "",
            label: res.decision_style_label || "",
            description: res.decision_style_description || "",
          });
        }
        
        // DecisionStyleを更新
        if (res.decision_style) {
          setDecisionStyle({
            name: res.decision_style,
            label: res.decision_style_label || res.decision_style,
            description: res.decision_style_description || "",
          });
        }
      } catch (error) {
        console.error("回答送信エラー:", error);
      } finally {
        setLoading(false);
      }
    },
    [sessionId, current, addAnswer, setProfile],
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
      router.push("/demo/service/recommend");
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
    <div className="mx-auto max-w-[840px] px-6 py-10">
      <div className="mb-8 text-center">
        <h2 className="text-2xl font-bold text-navy">
          あなたの価値観をお聞かせください
        </h2>
        <p className="mt-2 text-sm text-text-muted">
          質問 {step + 1} / {questions.length}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
        {/* 左: 質問カード */}
        <div>
          {/* 質問カード */}
          <div className="rounded-md border border-border bg-surface p-8 shadow-sm">
            <h3 className="mb-6 text-xl font-medium text-navy">{current.text}</h3>
            <div className="flex flex-col gap-3">
              {current.choices.map((choice) => (
                <button
                  key={choice.key}
                  type="button"
                  disabled={loading}
                  onClick={() => handleSelect(choice)}
                  className={`rounded-md border px-4 py-3 text-left text-base transition-colors ${
                    selectedKey === choice.key
                      ? "border-navy bg-navy/5 font-medium text-navy"
                      : "border-border bg-bg hover:border-navy-light hover:bg-surface"
                  }`}
                >
                  {choice.label}
                </button>
              ))}
            </div>
          </div>

          {selectedKey && (
            <div className="mt-8 flex justify-center">
              <PrimaryButton onClick={handleNext} disabled={loading}>
                {step < questions.length - 1 ? "次の質問へ" : "レコメンドを見る"}
              </PrimaryButton>
            </div>
          )}

          {/* 進捗インジケーター */}
          <div className="mt-12 flex justify-center gap-2">
            {questions.map((_, i) => (
              <div
                key={i}
                className={`h-2 w-8 rounded-full transition-colors ${
                  i < step
                    ? "bg-gold"
                    : i === step
                      ? "bg-navy"
                      : "bg-gray-200"
                }`}
              />
            ))}
          </div>
        </div>

        {/* 右: プロファイル & DecisionStyle */}
        <div className="space-y-4">
          <ProfileMap profile={profile} />
          <DecisionStylePanel decisionStyle={decisionStyle} />
        </div>
      </div>
    </div>
  );
}
