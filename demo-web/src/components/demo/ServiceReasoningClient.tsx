"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useRequireSession } from "@/hooks/useRequireSession";
import { api } from "@/lib/api-client";
import { PrimaryButton } from "./PrimaryButton";

// ─── 型定義 ──────────────────────────────────────────────────────────────────

type LoadDetail = {
  name: string;
  description: string;
  related_values: string[];
  trigger_count: number;
  threshold: number;
};

type ServiceWithScore = {
  id: string;
  title: string;
  one_liner?: string;
  pitch?: string;
  need_rationale?: string;
  score: number;
  matched_needs: string[];
  matched_loads: string[];
  value_alignment: number;
  need_score?: number;
  load_score?: number;
  value_score?: number;
};

type AnswerRecord = {
  question_index: number;
  question_id: string;
  answer_key: string;
};

// ─── 静的マスターデータ ────────────────────────────────────────────────────────

const VALUE_LABELS: Record<string, string> = {
  safety: "安全・安心",
  family: "家族との時間",
  efficiency: "効率・合理性",
  enjoyment: "楽しさ・充実感",
  adventure: "自己成長・学び",
};

const VALUE_BADGE_COLORS: Record<string, { bg: string; text: string; bar: string }> = {
  safety:    { bg: "bg-blue-50",   text: "text-blue-800",   bar: "bg-blue-500"   },
  family:    { bg: "bg-green-50",  text: "text-green-800",  bar: "bg-green-500"  },
  efficiency:{ bg: "bg-gray-50",   text: "text-gray-700",   bar: "bg-gray-500"   },
  enjoyment: { bg: "bg-purple-50", text: "text-purple-800", bar: "bg-purple-500" },
  adventure: { bg: "bg-orange-50", text: "text-orange-800", bar: "bg-orange-500" },
};

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

const ANSWER_LABELS: Record<string, string> = {
  reduce_hassle: "手間を省きたい",
  enhance_experience: "体験を高めたい",
  connect_community: "コミュニティとつながりたい",
  save_cost: "コストを抑えたい",
  flexible_usage: "柔軟に使いたい",
  enthusiast: "熱狂的なファン",
  pragmatic: "実用重視",
  selective: "厳選派",
  cautious: "慎重派",
  minimal: "ミニマリスト",
  active_member: "積極的な参加者",
  share_knowledge: "知識を共有したい",
  observe_learn: "観察・学習派",
  need_based: "必要なときだけ",
  independent: "自立派",
  ownership: "所有したい",
  subscription: "サブスクがいい",
  pay_per_use: "使った分だけ払いたい",
  sharing: "シェアしたい",
  hybrid: "状況に合わせたい",
  anticipate_prepare: "先を読んで備えたい",
  explore_options: "選択肢を探りたい",
  upgrade_quality: "質を上げたい",
  simplify_optimize: "シンプルに最適化したい",
  maintain_stable: "安定を維持したい",
};

const SERVICE_QUESTION_TEXTS: Record<string, string> = {
  sq1: "クルマに求める体験",
  sq2: "クルマの使い方",
  sq3: "購入・利用の判断基準",
  sq4: "コミュニティへの関わり方",
  sq5: "サービスの利用スタイル",
};

const RANK_BADGE: Record<number, { label: string; bg: string; text: string; border: string }> = {
  1: { label: "1位", bg: "bg-yellow-400", text: "text-yellow-900", border: "border-yellow-500" },
  2: { label: "2位", bg: "bg-gray-300",   text: "text-gray-700",   border: "border-gray-400"   },
  3: { label: "3位", bg: "bg-orange-300", text: "text-orange-900", border: "border-orange-400" },
};

// ─── サブコンポーネント ─────────────────────────────────────────────────────────

/** 分析ステップ（横型フロー）の1ブロック */
function FlowStep({
  num,
  title,
  items,
  colorClass,
}: {
  num: number;
  title: string;
  items: string[];
  colorClass: string;
}) {
  return (
    <div className="flex flex-col items-center text-center" style={{ minWidth: 140 }}>
      <div className={`flex h-9 w-9 items-center justify-center rounded-full text-white font-bold text-sm mb-2 ${colorClass}`}>
        {num}
      </div>
      <p className="text-xs font-semibold text-gray-600 mb-2">{title}</p>
      <div className="flex flex-col gap-1">
        {items.map((item, i) => (
          <span
            key={i}
            className="rounded-full bg-white border border-gray-200 px-2 py-0.5 text-[11px] text-gray-700 shadow-sm"
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

/** フローの矢印 */
function FlowArrow() {
  return (
    <div className="flex items-center px-2 pt-5">
      <svg width="28" height="16" viewBox="0 0 28 16" fill="none">
        <path
          d="M0 8 H22 M16 2 L24 8 L16 14"
          stroke="#94A3B8"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

/** 推薦理由カード（サービス1件分） */
function ServiceReasonCard({
  service,
  rank,
  valueScores,
}: {
  service: ServiceWithScore;
  rank: number;
  valueScores: Record<string, number>;
}) {
  const badge = RANK_BADGE[rank] ?? RANK_BADGE[3];

  // 最もスコアが高い価値観を特定（value_alignment が高い ≒ 主な価値観）
  const topValueEntry = Object.entries(valueScores).sort(([, a], [, b]) => b - a)[0];
  const topValueLabel = topValueEntry ? VALUE_LABELS[topValueEntry[0]] : null;

  // スコアバーの色
  const scoreColor =
    service.score >= 0.75 ? "bg-green-500" :
    service.score >= 0.5  ? "bg-blue-500"  : "bg-gray-400";

  return (
    <div className={`rounded-xl border-2 bg-white p-6 shadow-sm ${badge.border}`}>
      {/* ヘッダー */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold ${badge.bg} ${badge.text}`}>
            {badge.label}
          </span>
          <h4 className="text-lg font-bold text-navy leading-snug">{service.title}</h4>
        </div>
        <div className="text-right shrink-0 ml-4">
          <span className="text-2xl font-bold text-navy">{Math.round(service.score * 100)}</span>
          <span className="text-sm text-gray-500 ml-0.5">点</span>
          <p className="text-xs text-gray-400 mt-0.5">総合マッチスコア</p>
        </div>
      </div>

      {/* 総合スコアバー */}
      <div className="mb-5">
        <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${scoreColor}`}
            style={{ width: `${Math.round(service.score * 100)}%` }}
          />
        </div>
      </div>

      {/* スコア内訳 */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        <div className="rounded-lg bg-blue-50 p-3 text-center">
          <p className="text-xs text-blue-600 font-medium mb-1">価値観マッチ</p>
          <p className="text-xl font-bold text-blue-700">{Math.round(service.value_alignment * 100)}<span className="text-xs font-normal ml-0.5">%</span></p>
        </div>
        <div className="rounded-lg bg-yellow-50 p-3 text-center">
          <p className="text-xs text-yellow-700 font-medium mb-1">ニーズ対応</p>
          <p className="text-xl font-bold text-yellow-700">{Math.round((service.need_score ?? 0) * 100)}<span className="text-xs font-normal ml-0.5">%</span></p>
        </div>
        <div className="rounded-lg bg-orange-50 p-3 text-center">
          <p className="text-xs text-orange-600 font-medium mb-1">課題解消</p>
          <p className="text-xl font-bold text-orange-600">{Math.round((service.load_score ?? 0) * 100)}<span className="text-xs font-normal ml-0.5">%</span></p>
        </div>
      </div>

      {/* 推薦理由テキスト */}
      {(service.pitch || service.need_rationale) && (
        <div className="mb-4 rounded-lg bg-navy/5 p-4 border-l-4 border-navy">
          <p className="text-sm font-semibold text-navy mb-1">推薦のポイント</p>
          <p className="text-sm text-gray-700 leading-relaxed">
            {service.pitch || service.need_rationale}
          </p>
        </div>
      )}

      {/* マッチしたニーズ */}
      {service.matched_needs.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            対応するあなたのニーズ
          </p>
          <div className="flex flex-wrap gap-2">
            {service.matched_needs.map((need) => (
              <span
                key={need}
                className="flex items-center gap-1 rounded-full bg-yellow-100 border border-yellow-300 px-3 py-1 text-xs text-yellow-900"
              >
                <span className="text-yellow-500">✓</span>
                {NEED_LABELS[need] || need}
              </span>
            ))}
          </div>
          {topValueLabel && (
            <p className="mt-2 text-xs text-gray-500">
              あなたの <span className="font-semibold text-gray-700">「{topValueLabel}」</span> という価値観と強く一致しています
            </p>
          )}
        </div>
      )}

      {/* マッチしたLoad */}
      {service.matched_loads.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            解消できる懸念事項
          </p>
          <div className="flex flex-wrap gap-2">
            {service.matched_loads.map((load) => (
              <span
                key={load}
                className="flex items-center gap-1 rounded-full bg-amber-100 border border-amber-300 px-3 py-1 text-xs text-amber-900"
              >
                <span>⚡</span>
                {load}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── メインコンポーネント ───────────────────────────────────────────────────────

export function ServiceReasoningClient() {
  const router = useRouter();
  const sessionId = useRequireSession();

  const [services, setServices] = useState<ServiceWithScore[]>([]);
  const [valueScores, setValueScores] = useState<Record<string, number>>({});
  const [detectedLoads, setDetectedLoads] = useState<LoadDetail[]>([]);
  const [answers, setAnswers] = useState<AnswerRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [similarProfiles, setSimilarProfiles] = useState<{
    total_users: number;
    similar_users: number;
    similarity_rate: number;
  } | null>(null);
  const [decisionStyle, setDecisionStyle] = useState<{
    label: string;
    description: string;
    confidence: number | null;
  } | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    const sid = sessionId;

    async function fetchData() {
      try {
        setLoading(true);

        const [serviceData, sessionData] = await Promise.all([
          api.getServiceRecommendations(sid),
          api.getSession(sid),
        ]);

        setServices(serviceData.services || []);

        const answersFromApi = (sessionData.answers || []) as AnswerRecord[];
        setAnswers(answersFromApi.filter((a) => a.question_id.startsWith("sq")));

        const profileData = sessionData.profile as {
          profile?: Record<string, number>;
          detected_loads?: LoadDetail[];
          decision_style_label?: string;
          decision_style_description?: string;
          decision_style_confidence?: number;
        } | undefined;

        const profile = profileData?.profile || {};
        setValueScores({
          safety:    profile.score_safety    || 0,
          family:    profile.score_family    || 0,
          efficiency:profile.score_efficiency|| 0,
          enjoyment: profile.score_enjoyment || 0,
          adventure: profile.score_adventure || 0,
        });
        setDetectedLoads(profileData?.detected_loads || []);

        if (profileData?.decision_style_label) {
          setDecisionStyle({
            label:       profileData.decision_style_label,
            description: profileData.decision_style_description || "",
            confidence:  profileData.decision_style_confidence  || null,
          });
        }

        try {
          const similarData = await api.getSimilarProfiles(sid);
          setSimilarProfiles(similarData);
        } catch {
          /* 無視 */
        }
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
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-navy border-t-transparent" />
          <p className="mt-4 text-text-muted">分析結果を読み込み中...</p>
        </div>
      </div>
    );
  }

  // 価値観を降順ソート
  const sortedValues = Object.entries(valueScores).sort(([, a], [, b]) => b - a);
  const topValues = sortedValues.slice(0, 3);

  // フロー表示用データ
  const flowAnswerItems = answers.slice(0, 3).map((a) => ANSWER_LABELS[a.answer_key] || a.answer_key);
  const flowValueItems  = topValues.slice(0, 3).map(([k]) => VALUE_LABELS[k]);
  const flowNeedItems   = [...new Set(services.slice(0, 3).flatMap((s) => s.matched_needs))]
    .slice(0, 3)
    .map((n) => NEED_LABELS[n] || n);
  const flowLoadItems   = detectedLoads.slice(0, 2).map((l) => l.name);
  const flowServiceItems= services.slice(0, 3).map((s) => s.title);

  return (
    <div className="mx-auto max-w-[1100px] px-6 py-10">
      {/* ページヘッダー */}
      <div className="mb-10">
        <h2 className="text-3xl font-bold text-navy">提案の理由</h2>
        <p className="mt-2 text-text-muted">
          あなたの回答から価値観・ニーズ・懸念事項を分析し、最もマッチするサービスを選定しました
        </p>
      </div>

      {/* ══════════════════════════════════════════════════════════════
          セクション 1: 分析ステップのフロー
      ══════════════════════════════════════════════════════════════ */}
      <section className="mb-12">
        <h3 className="mb-4 text-xl font-semibold text-navy">分析の流れ</h3>
        <div className="rounded-xl border border-border bg-white p-6 shadow-sm">
          <div className="overflow-x-auto">
            <div className="flex items-start min-w-[720px]">
              <FlowStep
                num={1}
                title="質問への回答"
                items={flowAnswerItems.length > 0 ? flowAnswerItems : ["回答データなし"]}
                colorClass="bg-blue-500"
              />
              <FlowArrow />
              <FlowStep
                num={2}
                title="価値観の検出"
                items={flowValueItems.length > 0 ? flowValueItems : ["検出中"]}
                colorClass="bg-purple-500"
              />
              <FlowArrow />
              <FlowStep
                num={3}
                title="ニーズの特定"
                items={flowNeedItems.length > 0 ? flowNeedItems : ["特定中"]}
                colorClass="bg-yellow-500"
              />
              {flowLoadItems.length > 0 && (
                <>
                  <FlowArrow />
                  <FlowStep
                    num={4}
                    title="懸念事項の検出"
                    items={flowLoadItems}
                    colorClass="bg-orange-500"
                  />
                </>
              )}
              <FlowArrow />
              <FlowStep
                num={flowLoadItems.length > 0 ? 5 : 4}
                title="サービス推薦"
                items={flowServiceItems.length > 0 ? flowServiceItems : ["推薦中"]}
                colorClass="bg-navy"
              />
            </div>
          </div>
          <p className="mt-4 text-xs text-gray-400 text-center">
            ※ 価値観・ニーズ・懸念事項それぞれのマッチ度を合算してサービスをスコアリングしています
          </p>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
          セクション 2: あなたのプロファイル
      ══════════════════════════════════════════════════════════════ */}
      <section className="mb-12">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-semibold text-navy">あなたのプロファイル</h3>
          {similarProfiles && similarProfiles.total_users > 0 && (
            <p className="text-sm text-text-muted">
              類似ユーザー：
              <span className="font-semibold text-navy">{similarProfiles.similar_users}</span>
              /{similarProfiles.total_users} 名（{similarProfiles.similarity_rate}%）
            </p>
          )}
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {/* 価値観プロファイル */}
          <div className="rounded-xl border border-border bg-white p-5 shadow-sm">
            <p className="text-sm font-semibold text-navy mb-4">価値観プロファイル</p>
            <div className="space-y-3">
              {sortedValues.map(([key, score]) => {
                const colors = VALUE_BADGE_COLORS[key] ?? { bg: "bg-gray-50", text: "text-gray-700", bar: "bg-gray-400" };
                return (
                  <div key={key}>
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-xs font-medium ${colors.text}`}>
                        {VALUE_LABELS[key]}
                      </span>
                      <span className="text-xs text-gray-500">{Math.round(score)}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-gray-100 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${colors.bar}`}
                        style={{ width: `${Math.min(score, 100)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Decision スタイル */}
          <div className="rounded-xl border border-border bg-white p-5 shadow-sm">
            <p className="text-sm font-semibold text-navy mb-4">Decision スタイル</p>
            {decisionStyle ? (
              <>
                <div className="flex items-center gap-3 mb-3">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-navy text-white font-bold text-lg">
                    決
                  </div>
                  <div>
                    <p className="font-semibold text-navy">{decisionStyle.label}</p>
                    {decisionStyle.confidence !== null && (
                      <p className="text-xs text-gray-500">確信度 {Math.round(decisionStyle.confidence)}%</p>
                    )}
                  </div>
                </div>
                <p className="text-xs text-gray-600 leading-relaxed">{decisionStyle.description}</p>
              </>
            ) : (
              <p className="text-sm text-gray-400">データなし</p>
            )}
          </div>

          {/* 検出された懸念事項 */}
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-5 shadow-sm">
            <p className="text-sm font-semibold text-amber-900 mb-4">検出された懸念事項</p>
            {detectedLoads.length > 0 ? (
              <div className="space-y-3">
                {detectedLoads.map((load, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-300 text-xs font-bold text-amber-900 mt-0.5">
                      {idx + 1}
                    </span>
                    <div>
                      <p className="text-sm font-semibold text-amber-900">{load.name}</p>
                      {load.description && (
                        <p className="text-xs text-gray-600 mt-0.5">{load.description}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">懸念事項は検出されませんでした</p>
            )}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
          セクション 3: 質問と検出内容（補足情報）
      ══════════════════════════════════════════════════════════════ */}
      {answers.length > 0 && (
        <section className="mb-12">
          <h3 className="mb-4 text-xl font-semibold text-navy">質問から検出した内容</h3>
          <div className="rounded-xl border border-border bg-white p-6 shadow-sm">
            <div className="space-y-3">
              {answers.map((answer, idx) => (
                <div key={answer.question_id} className="flex items-start gap-4 py-3 border-b border-gray-100 last:border-0">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700 mt-0.5">
                    Q{idx + 1}
                  </span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-700">
                      {SERVICE_QUESTION_TEXTS[answer.question_id] || answer.question_id}
                    </p>
                    <div className="mt-1 flex flex-wrap gap-2">
                      <span className="rounded-full bg-blue-100 px-3 py-0.5 text-xs text-blue-700">
                        {ANSWER_LABELS[answer.answer_key] || answer.answer_key}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ══════════════════════════════════════════════════════════════
          セクション 4: 推薦サービスの詳細理由（メイン）
      ══════════════════════════════════════════════════════════════ */}
      <section className="mb-12">
        <h3 className="mb-2 text-xl font-semibold text-navy">なぜこのサービスが選ばれたか</h3>
        <p className="mb-5 text-sm text-gray-500">
          スコアは「価値観マッチ」「ニーズ対応」「懸念解消」の3軸を合算して算出しています
        </p>
        <div className="space-y-5">
          {services.slice(0, 3).map((service, idx) => (
            <ServiceReasonCard
              key={service.id}
              service={service}
              rank={idx + 1}
              valueScores={valueScores}
            />
          ))}
        </div>
      </section>

      {/* ナビゲーション */}
      <div className="mt-12 flex flex-wrap justify-center gap-4">
        <button
          onClick={() => router.push("/demo/service/recommend")}
          className="rounded-md border border-navy px-6 py-3 text-sm font-medium text-navy transition-colors hover:bg-navy/5"
        >
          サービス提案に戻る
        </button>
        <PrimaryButton onClick={() => router.push("/demo/opening")}>
          最初に戻る
        </PrimaryButton>
        <button
          onClick={() => router.push(`/demo/knowledge-base?session=${sessionId}`)}
          className="rounded-md bg-blue-600 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          業務知識基盤を見る
        </button>
        <button
          onClick={() => router.push("/demo/analytics")}
          className="rounded-md bg-gray-600 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-gray-700"
        >
          ログデータを見る
        </button>
      </div>
    </div>
  );
}
