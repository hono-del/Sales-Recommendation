"use client";

import type {
  ExperienceItem,
  FeatureCardItem,
  FilterFunnelData,
  ReasonTraceStep,
  ThinkingProcessData,
  VehicleDetail,
} from "@/types/graph";
import { DecisionStyleStorySection } from "./DecisionStyleStorySection";
import { KgCatalogCheckButton } from "./KgCatalogCheckModal";

type Props = {
  data: ThinkingProcessData;
  animationPhase: number;
  sessionId?: string;
  topModel?: string;
};

const STEP_COUNT = 6;

function stepVisible(animationPhase: number, stepIndex: number): boolean {
  return animationPhase > stepIndex;
}

export function ThinkingStoryView({
  data,
  animationPhase,
  sessionId,
  topModel,
}: Props) {
  return (
    <div className="mx-auto max-w-3xl space-y-16">
      <p className="text-center text-sm text-text-muted">
        あなたの価値観・Decisionスタイル → 負荷 → 体験 → 機能 → 車種のつながりを、順を追って可視化しています
      </p>

      {data.filter_funnel && (
        <FilterFunnelSection
          funnel={data.filter_funnel}
          visible={stepVisible(animationPhase, 0)}
        />
      )}

      <ValuesSection
        values={data.values}
        visible={stepVisible(animationPhase, 1)}
      />

      <DecisionStyleStorySection
        decisionStyle={data.decision_style}
        presentation={data.style_presentation}
        visible={stepVisible(animationPhase, 1)}
      />

      <LoadsSection loads={data.loads} visible={stepVisible(animationPhase, 2)} />

      <ExperiencesSection
        experiences={data.experiences}
        visible={stepVisible(animationPhase, 3)}
        sessionId={sessionId}
      />

      <FeaturesSection
        features={data.features}
        visible={stepVisible(animationPhase, 4)}
        sessionId={sessionId}
        topModel={topModel ?? data.vehicle?.name}
      />

      <VehicleSection vehicle={data.vehicle} visible={stepVisible(animationPhase, 5)} />

      {data.reason_trace && stepVisible(animationPhase, 5) && (
        <ReasonTraceSection steps={data.reason_trace.steps} />
      )}
    </div>
  );
}

function SectionShell({
  stepNum,
  title,
  description,
  accent,
  visible,
  children,
}: {
  stepNum: number;
  title: string;
  description: string;
  accent: string;
  visible: boolean;
  children: React.ReactNode;
}) {
  return (
    <section
      className={`transition-all duration-700 ${
        visible ? "translate-y-0 opacity-100" : "translate-y-6 opacity-0 pointer-events-none"
      }`}
      aria-hidden={!visible}
    >
      <div className="mb-6 flex items-start gap-4">
        <span
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white"
          style={{ background: accent }}
        >
          {stepNum}
        </span>
        <div>
          <h2 className="text-xl font-medium text-navy">{title}</h2>
          <p className="mt-1 text-sm text-text-muted">{description}</p>
        </div>
      </div>
      {children}
    </section>
  );
}

function FilterFunnelSection({
  funnel,
  visible,
}: {
  funnel: FilterFunnelData;
  visible: boolean;
}) {
  const { input, stages } = funnel;

  return (
    <SectionShell
      stepNum={0}
      title="候補の絞り込み"
      description="入力した条件で、候補がどのように減っていったかを示します。AIが勝手に決めたのではなく、合理的に絞り込まれています。"
      accent="#64748B"
      visible={visible}
    >
      <div className="rounded-xl border border-border bg-surface p-6">
        <div className="mb-6 flex flex-wrap gap-4 text-sm">
          <span className="rounded-full bg-slate-100 px-3 py-1">
            乗員 <strong>{input.family_size}人</strong>
          </span>
          <span className="rounded-full bg-slate-100 px-3 py-1">
            予算 <strong>{input.budget_label}</strong>
          </span>
          <span className="rounded-full bg-slate-100 px-3 py-1">
            利用シーン <strong>{input.lifestyle}</strong>
          </span>
        </div>

        <div className="space-y-4">
          {stages.map((stage, i) => (
            <div key={stage.filter_key ?? i} className="relative">
              {i > 0 && (
                <div className="absolute -top-3 left-6 text-slate-300" aria-hidden>
                  ↓
                </div>
              )}
              <div
                className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-white px-5 py-4 sm:flex-row sm:items-center sm:justify-between"
                style={{
                  animationDelay: `${i * 200}ms`,
                }}
              >
                <span className="font-medium text-navy">{stage.label}</span>
                <span className="text-2xl font-light tabular-nums text-navy">
                  {stage.count}
                  <span className="ml-1 text-sm text-text-muted">車種</span>
                </span>
              </div>
              {stage.excluded_reason && (
                <p className="mt-2 pl-2 text-xs leading-relaxed text-text-muted">
                  {stage.excluded_reason}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function ValuesSection({
  values,
  visible,
}: {
  values: { key: string; label: string; percent: number }[];
  visible: boolean;
}) {
  return (
    <SectionShell
      stepNum={1}
      title="あなたの価値観"
      description="あなたの回答から、重視する価値を抽出しています。"
      accent="#2563EB"
      visible={visible}
    >
      <ul className="space-y-3">
        {values.map((v) => (
          <li
            key={v.key}
            className="flex items-center justify-between rounded-lg border border-blue-100 bg-blue-50/50 px-5 py-4"
          >
            <span className="flex items-center gap-2 font-medium text-navy">
              <span className="text-blue-600">✓</span>
              {v.label}
            </span>
            <span className="text-sm tabular-nums text-text-muted">{v.percent}%</span>
          </li>
        ))}
      </ul>
    </SectionShell>
  );
}

function LoadsSection({ loads, visible }: { loads: string[]; visible: boolean }) {
  return (
    <SectionShell
      stepNum={2}
      title="検出された負荷"
      description="移動時のストレスや不安を検出しました。これらは「避けたいこと」として扱います。"
      accent="#DC2626"
      visible={visible}
    >
      <ul className="space-y-3">
        {loads.map((load) => (
          <li
            key={load}
            className="flex items-start gap-3 rounded-lg border border-red-100 bg-red-50/40 px-5 py-4 text-navy"
          >
            <span className="mt-0.5 text-red-600">✓</span>
            <span>{load}</span>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-xs text-text-muted">
        次のステップでは、これらの負荷と<strong>あなたの価値観</strong>を掛け合わせて「必要な体験」を導きます。
      </p>
    </SectionShell>
  );
}

function ExperiencesSection({
  experiences,
  visible,
  sessionId,
}: {
  experiences: ExperienceItem[];
  visible: boolean;
  sessionId?: string;
}) {
  return (
    <SectionShell
      stepNum={3}
      title="必要な体験（KG生活欲求）"
      description="価値観・負荷からナレッジグラフ上の Need に結びつけた、あなたに必要な移動体験です。"
      accent="#16A34A"
      visible={visible}
    >
      <div className="mb-4 flex flex-col items-center gap-3 sm:flex-row sm:justify-between">
        <div className="rounded-lg bg-green-50/80 px-4 py-3 text-center text-xs font-medium text-green-800 sm:flex-1">
          価値観・負荷 → KG Need → 機能・車種
        </div>
        {sessionId && (
          <KgCatalogCheckButton
            kind="needs"
            sessionId={sessionId}
            buttonLabel="Need一覧を確認"
          />
        )}
      </div>
      <div className="space-y-6">
        {experiences.map((exp) => (
          <article
            key={exp.need_name ?? exp.label}
            className="overflow-hidden rounded-xl border border-green-100 bg-white shadow-sm"
          >
            <div className="border-b border-green-100 bg-green-50/60 px-5 py-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-green-600">✓</span>
                <h3 className="font-semibold text-navy">{exp.label}</h3>
                {exp.need_group ? (
                  <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-800">
                    {exp.need_group}
                  </span>
                ) : null}
              </div>
              {exp.need_name ? (
                <p className="mt-1 text-xs text-text-muted">Need: {exp.need_name}</p>
              ) : null}
            </div>
            <div className="px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-green-700">
                {exp.why_title}
              </p>
              <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-text">
                {exp.why_body}
              </p>
            </div>
          </article>
        ))}
      </div>
    </SectionShell>
  );
}

const FEATURE_ICONS: Record<string, string> = {
  shield: "🛡️",
  leaf: "🌿",
  connect: "📡",
  map: "🗺️",
  voice: "🎙️",
  app: "📱",
  camera: "📷",
  seat: "💺",
  quiet: "🔇",
  entry: "🚪",
  brake: "⚙️",
  feature: "✨",
};

function FeaturesSection({
  features,
  visible,
  sessionId,
  topModel,
}: {
  features: FeatureCardItem[];
  visible: boolean;
  sessionId?: string;
  topModel?: string;
}) {
  return (
    <SectionShell
      stepNum={4}
      title="体験を支えるポイント"
      description="機能名ではなく、その先にある体験価値をお伝えします。"
      accent="#7C3AED"
      visible={visible}
    >
      {sessionId && (
        <div className="mb-4 flex justify-end">
          <KgCatalogCheckButton
            kind="features"
            sessionId={sessionId}
            topModel={topModel}
            buttonLabel="TechnicalFeature一覧を確認"
            className="rounded-md border border-purple-200 bg-white px-3 py-1.5 text-xs font-medium text-purple-900 shadow-sm hover:bg-purple-50"
          />
        </div>
      )}
      <div className="grid gap-6 sm:grid-cols-1">
        {features.map((feat) => (
          <article
            key={feat.name}
            className="rounded-2xl border border-purple-100 bg-gradient-to-br from-white to-purple-50/30 p-8 shadow-sm"
          >
            <div className="mb-4 flex items-center gap-3">
              <span className="text-3xl" aria-hidden>
                {FEATURE_ICONS[feat.icon ?? "feature"] ?? "✨"}
              </span>
              <span className="rounded-full bg-purple-100 px-2 py-0.5 text-[10px] font-medium text-purple-800">
                {feat.emotional_benefit}
              </span>
            </div>
            <h3 className="text-lg font-medium leading-snug text-navy">{feat.headline}</h3>
            <p className="mt-4 text-sm leading-relaxed text-text">{feat.body}</p>
            {feat.feature_name && (
              <p className="mt-3 rounded-md bg-purple-50 px-3 py-1.5 text-xs font-medium text-purple-800">
                機能・装備: {feat.feature_name}
              </p>
            )}
          </article>
        ))}
      </div>
    </SectionShell>
  );
}

function VehicleSection({
  vehicle,
  visible,
}: {
  vehicle: VehicleDetail;
  visible: boolean;
}) {
  const pct = Math.round(vehicle.score * 100);
  const displayName = vehicle.display_name || vehicle.name;

  return (
    <SectionShell
      stepNum={5}
      title="おすすめ車種"
      description="ここまでの積み上げから、最も相性の良い一台です。"
      accent="#B8920C"
      visible={visible}
    >
      <div className="overflow-hidden rounded-2xl border-2 border-[#B8920C]/40 bg-gradient-to-b from-[#FFFAF0] to-white shadow-md">
        <div className="px-8 py-10 text-center">
          <p className="text-3xl font-light text-navy">{displayName}</p>
          <div className="mt-4 flex items-center justify-center gap-2">
            <span className="text-sm text-text-muted">マッチスコア</span>
            <span className="text-4xl font-bold text-[#B8920C]">{pct}%</span>
          </div>
        </div>

        <div className="grid gap-4 border-t border-[#B8920C]/20 bg-white px-8 py-6 sm:grid-cols-2">
          {vehicle.seating_capacity != null && vehicle.seating_capacity > 0 && (
            <div>
              <p className="text-xs text-text-muted">乗車人数</p>
              <p className="mt-1 font-medium text-navy">{vehicle.seating_capacity}人</p>
            </div>
          )}
          {vehicle.price_range && (
            <div>
              <p className="text-xs text-text-muted">価格レンジ</p>
              <p className="mt-1 font-medium text-navy">{vehicle.price_range}</p>
            </div>
          )}
          {vehicle.fuel_type && (
            <div>
              <p className="text-xs text-text-muted">パワートレイン</p>
              <p className="mt-1 font-medium text-navy">{vehicle.fuel_type}</p>
            </div>
          )}
          {vehicle.lifestyle_fit && (
            <div className="sm:col-span-2">
              <p className="text-xs text-text-muted">ライフスタイル適合</p>
              <p className="mt-1 text-sm text-navy">{vehicle.lifestyle_fit}</p>
            </div>
          )}
        </div>

        <div className="border-t border-[#B8920C]/20 px-8 py-6">
          <p className="text-xs font-semibold text-navy">おすすめ理由</p>
          <p className="mt-2 text-sm leading-relaxed text-text">{vehicle.reason}</p>
        </div>

        {vehicle.confidence_points && vehicle.confidence_points.length > 0 && (
          <div className="border-t border-[#B8920C]/20 bg-[#FFFAF0]/50 px-8 py-6">
            <p className="text-xs font-semibold text-navy">安心して選べるポイント</p>
            <ul className="mt-3 space-y-2">
              {vehicle.confidence_points.map((pt) => (
                <li key={pt} className="flex items-start gap-2 text-sm text-text">
                  <span className="text-[#B8920C]">✓</span>
                  {pt}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </SectionShell>
  );
}

function ReasonTraceSection({ steps }: { steps: ReasonTraceStep[] }) {
  return (
    <section className="rounded-xl border border-border bg-slate-50 p-6">
      <h2 className="text-lg font-medium text-navy">提案の追跡（Reason Trace）</h2>
      <p className="mt-1 text-sm text-text-muted">
        なぜこの提案に至ったか、判断の流れを確認できます。
      </p>
      <ol className="mt-6 space-y-4">
        {steps.map((s, i) => (
          <li key={s.step} className="flex gap-4">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-navy text-xs font-bold text-white">
              {i + 1}
            </span>
            <div>
              <p className="text-sm font-semibold text-navy">{s.step}</p>
              <p className="mt-0.5 text-sm text-text-muted">{s.summary}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

export { STEP_COUNT };
