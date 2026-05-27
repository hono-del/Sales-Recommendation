"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";

interface ProfileInputClientProps {
  sessionId: string;
}

const FAMILY_SIZE_OPTIONS = [
  { value: 1, label: "1人" },
  { value: 2, label: "2人" },
  { value: 4, label: "3-4人" },
  { value: 6, label: "5-6人" },
  { value: 8, label: "7人以上" },
];

const BUDGET_OPTIONS = [
  { value: "~200", label: "~200万円" },
  { value: "200-300", label: "200-300万" },
  { value: "300-400", label: "300-400万" },
  { value: "400-500", label: "400-500万" },
  { value: "500~", label: "500万円~" },
];

export default function ProfileInputClient({ sessionId }: ProfileInputClientProps) {
  const router = useRouter();
  const [familySize, setFamilySize] = useState<number | null>(null);
  const [budgetRange, setBudgetRange] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!familySize || !budgetRange) {
      return;
    }

    setLoading(true);
    try {
      await api.postProfileInput(sessionId, {
        family_size: familySize,
        budget_range: budgetRange,
      });
      router.push("/demo/questions");
    } catch (error) {
      console.error("Failed to submit profile input:", error);
      alert("エラーが発生しました。もう一度お試しください。");
    } finally {
      setLoading(false);
    }
  };

  const canSubmit = familySize !== null && budgetRange !== null && !loading;

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center p-8"
      style={{ background: "var(--color-bg-base)" }}
    >
      <div
        className="w-full max-w-3xl p-12 rounded-lg shadow-lg"
        style={{ background: "var(--color-bg-panel)" }}
      >
        {/* タイトル */}
        <h1
          className="text-center text-4xl font-bold mb-3"
          style={{ color: "var(--color-navy)" }}
        >
          まず、基本的なことを教えてください
        </h1>
        <p
          className="text-center text-lg mb-12"
          style={{ color: "var(--color-text-muted)" }}
        >
          あなたに合った車を提案するため、2つの質問にお答えください
        </p>

        {/* 質問1: 乗車人数 */}
        <div className="mb-10">
          <h2
            className="text-2xl font-semibold mb-4"
            style={{ color: "var(--color-navy)" }}
          >
            普段、何人で車に乗ることが多いですか？
          </h2>
          <p
            className="text-sm mb-4"
            style={{ color: "var(--color-text-muted)" }}
          >
            ※ 家族構成や普段の乗車人数をお選びください
          </p>
          <div className="grid grid-cols-5 gap-4">
            {FAMILY_SIZE_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => setFamilySize(option.value)}
                className={`py-4 px-6 rounded-lg text-lg font-semibold transition-all ${
                  familySize === option.value
                    ? "ring-2"
                    : "hover:opacity-80"
                }`}
                style={{
                  background:
                    familySize === option.value
                      ? "var(--color-gold)"
                      : "var(--color-bg-base)",
                  color:
                    familySize === option.value
                      ? "white"
                      : "var(--color-navy)",
                  ringColor: "var(--color-gold)",
                }}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        {/* 質問2: 予算 */}
        <div className="mb-10">
          <h2
            className="text-2xl font-semibold mb-4"
            style={{ color: "var(--color-navy)" }}
          >
            予算の目安を教えてください
          </h2>
          <p
            className="text-sm mb-4"
            style={{ color: "var(--color-text-muted)" }}
          >
            ※ あくまで目安です。ご希望に応じて柔軟に提案します
          </p>
          <div className="grid grid-cols-5 gap-4">
            {BUDGET_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => setBudgetRange(option.value)}
                className={`py-4 px-6 rounded-lg text-lg font-semibold transition-all ${
                  budgetRange === option.value
                    ? "ring-2"
                    : "hover:opacity-80"
                }`}
                style={{
                  background:
                    budgetRange === option.value
                      ? "var(--color-gold)"
                      : "var(--color-bg-base)",
                  color:
                    budgetRange === option.value
                      ? "white"
                      : "var(--color-navy)",
                  ringColor: "var(--color-gold)",
                }}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        {/* 次へボタン */}
        <div className="flex justify-center mt-12">
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="py-4 px-16 rounded-lg text-xl font-bold transition-all"
            style={{
              background: canSubmit ? "var(--color-gold)" : "#ccc",
              color: "white",
              cursor: canSubmit ? "pointer" : "not-allowed",
              opacity: canSubmit ? 1 : 0.6,
            }}
          >
            {loading ? "送信中..." : "次へ（Questions）"}
          </button>
        </div>
      </div>
    </div>
  );
}
