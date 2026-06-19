"use client";

import { useEffect, useState } from "react";
import { useRequireSession } from "@/hooks/useRequireSession";
import { useDemoStore } from "@/stores/demoStore";
import { api } from "@/lib/api-client";
import { decisionStyleFromServiceSq0 } from "@/lib/decision-style-calculator";
import { ServiceOfferingSection } from "./ServiceOfferingSection";
import { PrimaryButton } from "./PrimaryButton";
import { useRouter } from "next/navigation";

type ServiceOffering = {
  id: string;
  title: string;
  one_liner: string;
  direction: "upgrade" | "downgrade" | "neutral";
  domain: string;
  score: number;
  matched_needs: string[];
  matched_loads: string[];
  value_alignment: number;
  pitch: string;
  need_rationale: string;
};

type FeedbackValue = "not_fit" | "low_interest" | "somewhat_interested" | "want_details";

export function ServiceRecommendClient() {
  const router = useRouter();
  const sessionId = useRequireSession();
  const answers = useDemoStore((s) => s.answers);
  const decisionStyleFromStore = useDemoStore((s) => s.decisionStyle);

  const [services, setServices] = useState<ServiceOffering[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedbacks, setFeedbacks] = useState<Record<string, FeedbackValue>>({});
  const [saving, setSaving] = useState(false);
  const [decisionStyle, setDecisionStyle] = useState<{
    name: string;
    label: string;
    description: string;
  } | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    
    const validSessionId = sessionId; // 型ガード

    async function fetchServices() {
      try {
        setLoading(true);
        setError(null);
        
        const data = await api.getServiceRecommendations(validSessionId);
        setServices((data.services || []) as ServiceOffering[]);
        
        // DecisionStyle: ストア → API → Q1回答 の順で取得
        const storeAnswers = useDemoStore.getState().answers;
        const styleFromAnswers = decisionStyleFromServiceSq0(storeAnswers);
        let resolvedStyle = decisionStyleFromStore ?? styleFromAnswers;

        if (!resolvedStyle) {
          console.log('[ServiceRecommend] DecisionStyle not in store, fetching from API');
          const sessionData = await api.getSession(validSessionId);
          const profileData = sessionData.profile as {
            decision_style?: string;
            decision_style_label?: string;
            decision_style_description?: string;
          } | undefined;

          if (profileData?.decision_style) {
            resolvedStyle = {
              name: profileData.decision_style,
              label: profileData.decision_style_label || profileData.decision_style,
              description: profileData.decision_style_description || "",
              confidence: 100,
              secondary: "",
              secondaryLabel: "",
              scores: { [profileData.decision_style]: 100 },
              isMixed: false,
            };
          } else {
            const apiAnswers = (sessionData.answers ?? []).map((a) => ({
              question_index: a.question_index,
              question_id: a.question_id,
              answer_key: a.answer_key,
            }));
            resolvedStyle = decisionStyleFromServiceSq0(apiAnswers);
          }
        }

        if (resolvedStyle) {
          console.log('[ServiceRecommend] DecisionStyle resolved:', resolvedStyle.name);
          setDecisionStyle({
            name: resolvedStyle.name,
            label: resolvedStyle.label,
            description: resolvedStyle.description,
          });
        } else {
          console.log('[ServiceRecommend] No DecisionStyle found');
        }
      } catch (e) {
        console.error("サービス推薦エラー:", e);
        setError(e instanceof Error ? e.message : "サービス推薦の取得に失敗しました");
      } finally {
        setLoading(false);
      }
    }

    fetchServices();
  }, [sessionId, decisionStyleFromStore]);

  const handleFeedbackChange = (serviceId: string, value: FeedbackValue) => {
    setFeedbacks((prev) => ({
      ...prev,
      [serviceId]: value,
    }));
  };

  const saveFeedbacks = async () => {
    if (!sessionId || Object.keys(feedbacks).length === 0 || saving) return;

    setSaving(true);
    try {
      // 全フィードバックを送信
      for (const [serviceId, feedbackValue] of Object.entries(feedbacks)) {
        const service = services.find((s) => s.id === serviceId);
        if (!service) continue;

        await api.postServiceFeedback(sessionId, {
          service_id: serviceId,
          service_rank: services.indexOf(service) + 1,
          service_score: service.score,
          feedback_value: feedbackValue,
          matched_needs: service.matched_needs,
          matched_loads: service.matched_loads,
          value_alignment: service.value_alignment,
        });
      }
      
      // 全フィードバック送信完了後、ログを1回だけ記録
      await api.logSessionAnalytics(sessionId);
    } catch (e) {
      console.error("フィードバック送信エラー:", e);
    } finally {
      setSaving(false);
    }
  };

  const handleNavigate = (path: string) => {
    router.push(path);
  };

  const handleSaveFeedback = async () => {
    await saveFeedbacks();
    alert("フィードバックを保存しました");
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-navy border-t-transparent"></div>
          <p className="mt-4 text-text-muted">
            あなたに最適なサービスを分析中...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-[840px] px-6 py-10">
        <div className="rounded-md border border-load/40 bg-load/10 p-6 text-center">
          <p className="mb-4 text-navy">{error}</p>
          <PrimaryButton onClick={() => router.push("/demo/opening")}>
            最初に戻る
          </PrimaryButton>
        </div>
      </div>
    );
  }

  // DecisionStyleに応じた表示設定
  const getDisplayConfig = () => {
    const styleName = decisionStyle?.name;
    console.log('[ServiceRecommend] getDisplayConfig - decisionStyle:', decisionStyle);
    console.log('[ServiceRecommend] styleName:', styleName);
    
    switch (styleName) {
      case "Maximizer":
        return {
          title: "あなたにおすすめのサービス（徹底比較型）",
          subtitle: "全てのサービスを詳しく比較し、最適な選択ができます",
          maxServices: services.length,
          layout: "comparison" as const,
          showDetailedScores: true,
        };
      case "Satisficer":
        return {
          title: "あなたに最適なサービス（十分型）",
          subtitle: "必要な条件を満たした最適なサービスをご提案します",
          maxServices: 5,
          layout: "hero" as const,
          showDetailedScores: false,
        };
      case "Authority-driven":
        return {
          title: "専門家が推奨するサービス",
          subtitle: "✓ 実績と信頼性で選ばれたトップクラスのサービス",
          maxServices: services.length,
          layout: "authority" as const,
          showDetailedScores: false,
        };
      case "Delegator":
        return {
          title: "多くの方に選ばれているサービス",
          subtitle: "👥 あなたと同じ条件の方に人気のサービス",
          maxServices: 7,
          layout: "popular" as const,
          showDetailedScores: false,
        };
      case "Intuitive":
        return {
          title: "あなたの直感が選ぶベストサービス",
          subtitle: "✨ 魅力的な体験と充実感を提供するサービス",
          maxServices: services.length,
          layout: "visual" as const,
          showDetailedScores: false,
        };
      case "Impulsive":
        return {
          title: "今すぐ始められるサービス（即決型）",
          subtitle: "期間限定の特別なご提案です",
          maxServices: services.length,
          layout: "urgent" as const,
          showDetailedScores: false,
        };
      default:
        console.log('[ServiceRecommend] Using default layout');
        return {
          title: "あなたにおすすめのサービス",
          subtitle: "ご回答いただいた価値観から、最適なサービスを提案します",
          maxServices: services.length,
          layout: "default" as const,
          showDetailedScores: false,
        };
    }
  };

  const displayConfig = getDisplayConfig();
  console.log('[ServiceRecommend] displayConfig:', displayConfig);
  const displayedServices = services.slice(0, displayConfig.maxServices);

  return (
    <div className="mx-auto max-w-[1024px] px-6 py-10">
      {/* DecisionStyle表示 */}
      {decisionStyle && (
        <div className="mb-6 rounded-lg border border-navy/20 bg-navy/5 p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-navy text-white font-bold">
              決
            </div>
            <div>
              <p className="text-sm font-semibold text-navy">{decisionStyle.label}</p>
              <p className="text-xs text-text-muted">{decisionStyle.description}</p>
            </div>
          </div>
        </div>
      )}
      
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-navy">
          {displayConfig.title}
        </h2>
        <p className="mt-2 text-text-muted">
          {displayConfig.subtitle}
        </p>
      </div>

      {answers.length > 0 && (
        <div className="mb-6 rounded-md border border-border bg-surface p-4">
          <h3 className="mb-2 text-sm font-medium text-navy">回答内容</h3>
          <div className="flex flex-wrap gap-2">
            {answers.map((a) => (
              <span
                key={a.question_id}
                className="rounded-full bg-navy/10 px-3 py-1 text-xs text-navy"
              >
                Q{a.question_index}
              </span>
            ))}
          </div>
        </div>
      )}

      <ServiceOfferingSection 
        services={displayedServices} 
        loading={false} 
        feedbacks={feedbacks}
        onFeedbackChange={handleFeedbackChange}
        layout={displayConfig.layout}
        showDetailedScores={displayConfig.showDetailedScores}
      />

      {displayedServices.length > 0 && (
        <div className="mt-8 text-center">
          <p className="text-sm text-text-muted">
            これらのサービスについて、詳しくお知りになりたい場合はお問い合わせください
          </p>
          {displayedServices.length < services.length && (
            <p className="mt-2 text-xs text-text-muted">
              （全{services.length}件中、上位{displayedServices.length}件を表示）
            </p>
          )}
        </div>
      )}

      <div className="mt-12 flex justify-center gap-4">
        <button
          onClick={() => handleNavigate("/demo/service/reasoning")}
          className="rounded-md border border-navy px-6 py-3 text-sm font-medium text-navy transition-colors hover:bg-navy/5"
        >
          提案の理由を見る
        </button>
        <button
          onClick={handleSaveFeedback}
          disabled={saving || Object.keys(feedbacks).length === 0}
          className={`rounded-md bg-green-600 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-green-700 ${
            saving || Object.keys(feedbacks).length === 0 ? "opacity-50 cursor-not-allowed" : ""
          }`}
        >
          {saving ? "保存中..." : "FBを保存"}
        </button>
        <PrimaryButton 
          onClick={() => handleNavigate("/demo/opening")}
        >
          最初に戻る
        </PrimaryButton>
      </div>
    </div>
  );
}
