"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useRequireSession } from "@/hooks/useRequireSession";
import { useDemoStore } from "@/stores/demoStore";
import { api } from "@/lib/api-client";
import { PrimaryButton } from "./PrimaryButton";
import { ServiceKnowledgeGraph } from "./ServiceKnowledgeGraph";

type LoadDetail = {
  name: string;
  description: string;
  related_values: string[];
  trigger_count: number;
  threshold: number;
};

type AnalysisResult = {
  question_id: string;
  question_text: string;
  answer_text: string;
  answer_label: string;
  detected_values: string[];
  detected_needs: string[];
};

type ServiceWithScore = {
  id: string;
  title: string;
  score: number;
  matched_needs: string[];
  matched_loads: string[];
  value_alignment: number;
  // 個別スコア（v2.1追加、オプショナル）
  need_score?: number;
  load_score?: number;
  value_score?: number;
};

// Need name（英語コード）→ ラベル（日本語）のマッピング
const NEED_LABELS: Record<string, string> = {
  LowPhysicalBurden: "身体負担を減らしたい",
  EasyEntryExit: "乗り降りを楽にしたい",
  EfficientDailyMobility: "日常移動コストを抑えたい",
  StressFreeCommute: "通勤ストレスを減らしたい",
  PremiumFeeling: "上質感を感じたい",
  SmoothRideComfort: "乗り心地を良くしたい",
  QuietCabinExperience: "静かな空間で移動したい",
  RelaxingDrive: "リラックスして運転したい",
  FamilyConversation: "家族で会話しやすい空間が欲しい",
  WeekendFamilyTrip: "家族旅行を楽しみたい",
  OutdoorLifestyle: "アウトドア生活を楽しみたい",
  MaintenanceCostReduction: "維持費を抑えたい",
  LowFuelAnxiety: "燃料代不安を減らしたい",
  FlexibleCargoSpace: "荷物量に柔軟対応したい",
  FlatSeatUtility: "車中泊や大きな荷物に対応したい",
  ShortTripEfficiency: "短距離移動を効率化したい",
  DrivingConfidence: "運転への不安を減らしたい",
  AccidentAnxietyReduction: "事故不安を減らしたい",
  EnvironmentalResponsibility: "環境配慮したい",
  LongTermReliability: "長く安心して乗りたい",
  EasyParking: "駐車を楽にしたい",
  CrimeAnxietyReduction: "防犯不安を減らしたい",
  FamilyComfort: "家族全員が快適に移動したい",
  DrivingEnjoyment: "運転そのものを楽しみたい",
  PersonalExpression: "自分らしさを表現したい",
  AdventureLifestyle: "冒険感を楽しみたい",
  EmotionalAttachment: "愛着を持てる車に乗りたい",
};

// 回答キーから価値観を抽出
const ANSWER_TO_VALUES: Record<string, string[]> = {
  reduce_hassle: ["効率・合理性"],
  enhance_experience: ["楽しさ・充実感"],
  connect_community: ["家族との時間"],
  save_cost: ["効率・合理性"],
  flexible_usage: ["効率・合理性"],
  enthusiast: ["自己成長・学び"],
  pragmatic: ["効率・合理性"],
  selective: ["効率・合理性"],
  cautious: ["安全・安心"],
  minimal: ["効率・合理性"],
  active_member: ["家族との時間"],
  share_knowledge: ["家族との時間"],
  observe_learn: ["自己成長・学び"],
  need_based: ["効率・合理性"],
  independent: ["楽しさ・充実感"],
  ownership: ["楽しさ・充実感"],
  subscription: ["効率・合理性"],
  pay_per_use: ["効率・合理性"],
  sharing: ["効率・合理性"],
  hybrid: ["効率・合理性"],
  anticipate_prepare: ["安全・安心"],
  explore_options: ["自己成長・学び"],
  upgrade_quality: ["楽しさ・充実感"],
  simplify_optimize: ["効率・合理性"],
  maintain_stable: ["安全・安心"],
};

export function ServiceReasoningClient() {
  const router = useRouter();
  const sessionId = useRequireSession();

  const [analysisResults, setAnalysisResults] = useState<AnalysisResult[]>([]);
  const [services, setServices] = useState<ServiceWithScore[]>([]);
  const [valueScores, setValueScores] = useState<Record<string, number>>({});
  const [detectedLoads, setDetectedLoads] = useState<LoadDetail[]>([]);
  const [needToValues, setNeedToValues] = useState<Record<string, string[]>>({});
  const [allNeeds, setAllNeeds] = useState<string[]>([]);
  const [allLoads, setAllLoads] = useState<string[]>([]);
  const [allServices, setAllServices] = useState<Array<{
    id: string;
    title: string;
    one_liner: string;
  }>>([]);
  const [needMapping, setNeedMapping] = useState<Record<string, Record<string, string[]>>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!sessionId) return;
    
    const validSessionId = sessionId; // 型ガード

    async function fetchData() {
      try {
        setLoading(true);
        
        // サービス推薦結果を取得
        const serviceData = await api.getServiceRecommendations(validSessionId);
        setServices(serviceData.services || []);

        // セッションプロファイルを取得（価値観スコア + detected_loads + need_to_values + answers）
        const sessionData = await api.getSession(validSessionId);
        console.log("[ServiceReasoning] sessionData:", sessionData);
        
        // APIから回答データを取得
        const answersFromApi = (sessionData.answers || []) as Array<{
          question_index: number;
          question_id: string;
          answer_key: string;
        }>;
        console.log("[ServiceReasoning] answersFromApi (v2):", answersFromApi);
        
        const profileData = sessionData.profile as { 
          profile?: Record<string, number>; 
          detected_loads?: LoadDetail[]; 
          need_to_values?: Record<string, string[]>;
        } | undefined;
        const profile = profileData?.profile || {};
        const loads = profileData?.detected_loads || [];
        const needToValuesData = profileData?.need_to_values || {};
        console.log("[ServiceReasoning] profile:", profile);
        console.log("[ServiceReasoning] detected_loads:", loads);
        console.log("[ServiceReasoning] need_to_values:", needToValuesData);
        setValueScores({
          safety: profile.score_safety || 0,
          family: profile.score_family || 0,
          efficiency: profile.score_efficiency || 0,
          enjoyment: profile.score_enjoyment || 0,
          adventure: profile.score_adventure || 0,
        });
        setDetectedLoads(loads);
        setNeedToValues(needToValuesData);

        // マスターデータを取得
        const masterData = await api.getMasterData();
        setAllNeeds(masterData.all_needs || []);
        setAllLoads(masterData.all_loads || []);
        setAllServices(masterData.all_services || []);

        // Need マッピングを取得
        const mappingData = await api.getNeedMapping();
        const answerToNeeds = mappingData.answer_to_needs || {};
        setNeedMapping(answerToNeeds);

        // サービス質問（sq1-sq5）のみをフィルタリング
        const serviceAnswers = answersFromApi.filter(a => a.question_id.startsWith('sq'));
        console.log("[ServiceReasoning] serviceAnswers:", serviceAnswers);
        console.log("[ServiceReasoning] answerToNeeds:", answerToNeeds);

        // 質問分析結果を生成（Need マッピング適用）
        const results: AnalysisResult[] = serviceAnswers.map((answer) => {
          const questionMapping = answerToNeeds[answer.question_id] || {};
          const needs = questionMapping[answer.answer_key] || [];
          console.log(`[ServiceReasoning] ${answer.question_id} -> ${answer.answer_key} -> needs:`, needs);
          return {
            question_id: answer.question_id,
            question_text: answer.question_id,
            answer_text: answer.answer_key,
            answer_label: answer.answer_key,
            detected_values: ANSWER_TO_VALUES[answer.answer_key] || ["効率・合理性"],
            detected_needs: needs,
          };
        });
        setAnalysisResults(results);
      } catch (e) {
        console.error("分析結果取得エラー:", e);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [sessionId]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-navy border-t-transparent"></div>
          <p className="mt-4 text-text-muted">分析結果を読み込み中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-10">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-navy">提案の理由</h2>
        <p className="mt-2 text-text-muted">
          あなたの回答から分析した価値観と、サービスのマッチングを可視化します
        </p>
      </div>

      {/* セクション1: 質問分析結果 */}
      <section className="mb-12">
        <h3 className="mb-4 text-xl font-semibold text-navy">
          質問から分析した内容
        </h3>
        <div className="space-y-4">
          {analysisResults.map((result, idx) => (
            <div
              key={result.question_id}
              className="rounded-lg border border-border bg-surface p-6"
            >
              <div className="mb-2 flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-navy text-xs font-bold text-white">
                  Q{idx + 1}
                </span>
                <h4 className="font-medium text-navy">質問{idx + 1}</h4>
              </div>
              <p className="mb-3 text-sm text-text-muted">
                回答キー: {result.answer_label}
              </p>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="mb-1 font-medium text-navy">検出された価値観</p>
                  <div className="flex flex-wrap gap-2">
                    {result.detected_values.map((value, i) => (
                      <span key={i} className="rounded-full bg-gold/20 px-3 py-1 text-xs text-gold-dark">
                        {value}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="mb-1 font-medium text-navy">関連するニーズ</p>
                  <div className="flex flex-wrap gap-2">
                    {result.detected_needs.slice(0, 3).map((need, i) => (
                      <span key={i} className="rounded-full bg-blue-100 px-3 py-1 text-xs text-blue-700">
                        {need}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* セクション2: 価値観スコア */}
      <section className="mb-12">
        <h3 className="mb-4 text-xl font-semibold text-navy">
          あなたの価値観プロファイル
        </h3>
        <div className="rounded-lg border border-border bg-surface p-6">
          <div className="space-y-4">
            {Object.entries(valueScores)
              .sort(([, a], [, b]) => b - a)
              .map(([key, score]) => {
                const labels: Record<string, string> = {
                  safety: "安全・安心",
                  family: "家族との時間",
                  efficiency: "効率・合理性",
                  enjoyment: "楽しさ・充実感",
                  adventure: "自己成長・学び",
                };
                return (
                  <div key={key}>
                    <div className="mb-1 flex items-center justify-between">
                      <span className="text-sm font-medium text-navy">
                        {labels[key]}
                      </span>
                      <span className="text-sm text-text-muted">
                        {Math.round(score)}%
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-gray-200">
                      <div
                        className="h-full rounded-full bg-navy transition-all"
                        style={{ width: `${Math.min(score, 100)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      </section>

      {/* セクション2.5: 検出された懸念事項（Load） */}
      {detectedLoads.length > 0 && (
        <section className="mb-12">
          <h3 className="mb-4 text-xl font-semibold text-navy">
            検出された懸念事項（Load）
          </h3>
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-6">
            <p className="mb-4 text-sm text-gray-700">
              あなたの回答から、以下の懸念事項が検出されました。これらに対応するサービスを優先的に推薦しています。
            </p>
            <div className="space-y-4">
              {detectedLoads.map((load, idx) => (
                <div
                  key={idx}
                  className="rounded-lg border border-amber-300 bg-white p-4"
                >
                  <div className="flex items-start gap-3">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-amber-200 text-sm font-bold text-amber-900">
                      {idx + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <h4 className="font-semibold text-amber-900 mb-2">
                        {load.name}
                      </h4>
                      {load.description && (
                        <p className="text-sm text-gray-700 mb-2">
                          {load.description}
                        </p>
                      )}
                      {load.related_values.length > 0 && (
                        <div className="flex flex-wrap gap-2 items-center">
                          <span className="text-xs text-gray-600">関連価値観:</span>
                          {load.related_values.map((value, vIdx) => (
                            <span
                              key={vIdx}
                              className="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700 border border-blue-200"
                            >
                              {value}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* セクション3: サービスマッチング */}
      <section className="mb-12">
        <h3 className="mb-4 text-xl font-semibold text-navy">
          サービスとのマッチング
        </h3>
        <div className="space-y-4">
          {services.slice(0, 3).map((service) => (
            <div
              key={service.id}
              className="rounded-lg border border-border bg-surface p-6"
            >
              <h4 className="mb-3 text-lg font-semibold text-navy">
                {service.title}
              </h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="mb-2 font-medium text-navy">
                    Need Match: {Math.round((service.need_score || 0) * 100)}%
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {service.matched_needs.slice(0, 3).map((need) => (
                      <span
                        key={need}
                        className="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700"
                      >
                        {need}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="mb-2 font-medium text-navy">
                    Load Match: {Math.round((service.load_score || 0) * 100)}%
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {service.matched_loads.length > 0 ? (
                      service.matched_loads.map((load) => (
                        <span
                          key={load}
                          className="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900 border border-amber-300"
                        >
                          {load}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-text-muted">なし</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* セクション4: ナレッジグラフ風ビジュアル */}
      <section className="mb-12">
        <h3 className="mb-4 text-xl font-semibold text-navy">
          分析フローの可視化
        </h3>
        <div className="rounded-lg border border-border bg-surface p-8">
          <ServiceKnowledgeGraph
            values={Object.entries(valueScores)
              .map(([key, score]) => {
                const labels: Record<string, string> = {
                  safety: "安全・安心",
                  family: "家族との時間",
                  efficiency: "効率・合理性",
                  enjoyment: "楽しさ・充実感",
                  adventure: "自己成長・学び",
                };
                return { key, label: labels[key], score };
              })
              .sort((a, b) => b.score - a.score)}
            needs={[
              ...new Set(
                services.slice(0, 3).flatMap((s) => 
                  s.matched_needs.map((n: string) => NEED_LABELS[n] || n)
                )
              ),
            ].slice(0, 5)}
            services={services.slice(0, 3).map((s) => ({
              id: s.id,
              title: s.title,
              matched_needs: s.matched_needs.map((n: string) => NEED_LABELS[n] || n),
            }))}
            needToValues={Object.fromEntries(
              Object.entries(needToValues).map(([needCode, valueKeys]) => [
                NEED_LABELS[needCode] || needCode,
                valueKeys
              ])
            )}
          />
          <div className="mt-4 text-center text-sm text-text-muted">
            <p>矢印の濃さは関連度の強さを表します</p>
            <p className="mt-1">
              <span className="inline-block h-3 w-3 rounded-sm bg-blue-200 border border-blue-500"></span>
              {" "}価値観{" "}
              <span className="inline-block h-3 w-3 rounded-sm bg-yellow-200 border border-yellow-500 ml-3"></span>
              {" "}ニーズ{" "}
              <span className="inline-block h-3 w-3 rounded-sm bg-indigo-200 border border-indigo-500 ml-3"></span>
              {" "}サービス
            </p>
          </div>
        </div>
      </section>

      {/* セクション5: マッチング概要 */}
      <section className="mb-12">
        <h3 className="mb-4 text-xl font-semibold text-navy">
          マッチング概要
        </h3>
        <p className="mb-6 text-sm text-text-muted">
          全体のデータの中から、あなたの回答にマッチしたニーズ・懸念事項・サービスを表示しています
        </p>
        
        {/* 統計カード */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          {/* ニーズ統計 */}
          <div className="rounded-lg border border-border bg-surface p-6">
            <div className="flex items-center gap-3 mb-4">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 text-lg">
                🎯
              </span>
              <div>
                <h4 className="font-semibold text-navy">ニーズ</h4>
                <p className="text-xs text-text-muted">Needs</p>
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-blue-600">
                {[...new Set(services.flatMap((s) => s.matched_needs))].length}
              </span>
              <span className="text-sm text-text-muted">/ 全{allNeeds.length}種類</span>
            </div>
            <p className="mt-2 text-xs text-text-muted">
              がマッチしました
            </p>
          </div>

          {/* Load統計 */}
          <div className="rounded-lg border border-border bg-surface p-6">
            <div className="flex items-center gap-3 mb-4">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-100 text-lg">
                ⚠️
              </span>
              <div>
                <h4 className="font-semibold text-navy">懸念事項</h4>
                <p className="text-xs text-text-muted">Loads</p>
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-amber-600">
                {detectedLoads.length}
              </span>
              <span className="text-sm text-text-muted">/ 全{allLoads.length}種類</span>
            </div>
            <p className="mt-2 text-xs text-text-muted">
              が検出されました
            </p>
          </div>

          {/* サービス統計 */}
          <div className="rounded-lg border border-border bg-surface p-6">
            <div className="flex items-center gap-3 mb-4">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-100 text-lg">
                📦
              </span>
              <div>
                <h4 className="font-semibold text-navy">サービス</h4>
                <p className="text-xs text-text-muted">Services</p>
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-indigo-600">
                {services.length}
              </span>
              <span className="text-sm text-text-muted">/ 全{allServices.length}種類</span>
            </div>
            <p className="mt-2 text-xs text-text-muted">
              を推薦しました
            </p>
          </div>
        </div>

        {/* 詳細リスト */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* ニーズ詳細リスト */}
          <div className="rounded-lg border border-border bg-surface p-6">
            <h4 className="mb-4 font-semibold text-navy flex items-center gap-2">
              <span className="text-sm">🎯</span>
              ニーズ一覧
            </h4>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {allNeeds.map((needCode) => {
                const needLabel = NEED_LABELS[needCode] || needCode;
                // 英語コードまたは日本語ラベルのどちらかでマッチを確認
                const isMatched = services.some(s => 
                  s.matched_needs.includes(needLabel) || s.matched_needs.includes(needCode)
                );
                
                return (
                  <div
                    key={needCode}
                    className={`rounded px-3 py-2 text-xs ${
                      isMatched
                        ? "bg-blue-100 text-blue-800 font-medium border border-blue-300"
                        : "bg-gray-50 text-gray-500"
                    }`}
                  >
                    {needLabel}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Load詳細リスト */}
          <div className="rounded-lg border border-border bg-surface p-6">
            <h4 className="mb-4 font-semibold text-navy flex items-center gap-2">
              <span className="text-sm">⚠️</span>
              懸念事項一覧
            </h4>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {allLoads.map((loadName) => {
                const isDetected = detectedLoads.some(l => l.name === loadName);
                
                return (
                  <div
                    key={loadName}
                    className={`rounded px-3 py-2 text-xs ${
                      isDetected
                        ? "bg-amber-100 text-amber-900 font-medium border border-amber-300"
                        : "bg-gray-50 text-gray-500"
                    }`}
                  >
                    {loadName}
                  </div>
                );
              })}
            </div>
          </div>

          {/* サービス詳細リスト */}
          <div className="rounded-lg border border-border bg-surface p-6">
            <h4 className="mb-4 font-semibold text-navy flex items-center gap-2">
              <span className="text-sm">📦</span>
              サービス一覧
            </h4>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {allServices.map((service) => {
                const matchedService = services.find(s => s.id === service.id);
                const isMatched = !!matchedService;
                const score = matchedService ? Math.round(matchedService.score * 100) : 0;
                
                return (
                  <div
                    key={service.id}
                    className={`rounded px-3 py-2 text-xs ${
                      isMatched
                        ? "bg-indigo-100 text-indigo-900 font-medium border border-indigo-300"
                        : "bg-gray-50 text-gray-500"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="flex-1">{service.title}</span>
                      {isMatched && (
                        <span className="shrink-0 font-bold text-indigo-700">
                          {score}%
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      <div className="mt-12 flex justify-center gap-4">
        <button
          onClick={() => router.push("/demo/service/recommend")}
          className="rounded-md border border-navy px-6 py-3 text-sm font-medium text-navy transition-colors hover:bg-navy/5"
        >
          サービス提案に戻る
        </button>
        <PrimaryButton onClick={() => router.push("/demo/opening")}>
          最初に戻る
        </PrimaryButton>
      </div>
    </div>
  );
}
