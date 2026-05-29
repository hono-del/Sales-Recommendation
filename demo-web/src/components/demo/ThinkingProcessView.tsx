"use client";

import { useEffect, useState } from "react";

type ValueItem = {
  key: string;
  label: string;
  percent: number;
};

type LoadItem = string;

type ExperienceItem = {
  label: string;
  description: string;
};

type FeatureItem = {
  name: string;
  reason: string;
};

type VehicleItem = {
  name: string;
  score: number;
  reason: string;
};

type Props = {
  values: ValueItem[];
  loads: LoadItem[];
  experiences: ExperienceItem[];
  features: FeatureItem[];
  vehicle: VehicleItem;
  animationPhase: number;
};

const STEP_LABELS = [
  "あなたの価値観",
  "検出された負荷",
  "必要な体験",
  "必要な機能",
  "おすすめ車種",
];

const STEP_DESCRIPTIONS = [
  "あなたの回答から、重視する価値を抽出しています。",
  "移動時のストレスや不安を検出しました。",
  "これらの体験が必要だと判断しました。",
  "体験を実現するための機能です。",
  "最も相性の良い車種です。",
];

export function ThinkingProcessView({
  values,
  loads,
  experiences,
  features,
  vehicle,
  animationPhase,
}: Props) {
  const [visibleSteps, setVisibleSteps] = useState<number[]>([]);

  useEffect(() => {
    if (animationPhase === 0) {
      setVisibleSteps([]);
      return;
    }
    
    const stepIndex = Math.min(animationPhase - 1, 4);
    setVisibleSteps((prev) => {
      if (prev.includes(stepIndex)) return prev;
      return [...prev, stepIndex];
    });
  }, [animationPhase]);

  const showArrow = (index: number) => visibleSteps.includes(index) && visibleSteps.includes(index + 1);

  return (
    <div className="relative w-full pb-6">
      <div className="flex items-start justify-center gap-3 px-2">
        {/* Step 1: Values */}
        <StepCard
          index={0}
          label={STEP_LABELS[0]}
          description={STEP_DESCRIPTIONS[0]}
          visible={visibleSteps.includes(0)}
          accentColor="blue"
        >
          <ul className="space-y-1.5">
            {values.slice(0, 3).map((v) => (
              <li key={v.key} className="flex items-center gap-1.5 text-xs">
                <span className="text-blue-600 text-sm">✓</span>
                <span className="font-medium text-navy">{v.label}</span>
              </li>
            ))}
          </ul>
        </StepCard>

        {showArrow(0) && <Arrow />}

        {/* Step 2: Loads */}
        <StepCard
          index={1}
          label={STEP_LABELS[1]}
          description={STEP_DESCRIPTIONS[1]}
          visible={visibleSteps.includes(1)}
          accentColor="red"
        >
          <ul className="space-y-1.5">
            {loads.slice(0, 3).map((load, i) => (
              <li key={i} className="flex items-center gap-1.5 text-xs">
                <span className="text-red-600 text-sm">✓</span>
                <span className="text-navy">{load}</span>
              </li>
            ))}
          </ul>
        </StepCard>

        {showArrow(1) && <Arrow />}

        {/* Step 3: Experiences */}
        <StepCard
          index={2}
          label={STEP_LABELS[2]}
          description={STEP_DESCRIPTIONS[2]}
          visible={visibleSteps.includes(2)}
          accentColor="green"
        >
          <ul className="space-y-1.5">
            {experiences.slice(0, 3).map((exp, i) => (
              <li key={i} className="text-xs">
                <div className="flex items-center gap-1.5">
                  <span className="text-green-600 text-sm">✓</span>
                  <span className="font-medium text-navy">{exp.label}</span>
                </div>
              </li>
            ))}
          </ul>
        </StepCard>

        {showArrow(2) && <Arrow />}

        {/* Step 4: Features */}
        <StepCard
          index={3}
          label={STEP_LABELS[3]}
          description={STEP_DESCRIPTIONS[3]}
          visible={visibleSteps.includes(3)}
          accentColor="purple"
        >
          <ul className="space-y-2">
            {features.slice(0, 3).map((feat, i) => (
              <li key={i} className="text-xs">
                <div className="font-medium text-navy">{feat.name}</div>
                <div className="mt-0.5 text-[10px] text-text-muted">→ {feat.reason}</div>
              </li>
            ))}
          </ul>
        </StepCard>

        {showArrow(3) && <Arrow />}

        {/* Step 5: Vehicle */}
        <StepCard
          index={4}
          label={STEP_LABELS[4]}
          description={STEP_DESCRIPTIONS[4]}
          visible={visibleSteps.includes(4)}
          accentColor="gold"
          wide
        >
          <div className="text-center">
            <div className="text-lg font-bold text-navy">{vehicle.name}</div>
            <div className="mt-2 flex items-center justify-center gap-1.5">
              <span className="text-[10px] text-text-muted">マッチスコア</span>
              <span className="text-2xl font-bold text-[#B8920C]">{Math.round(vehicle.score * 100)}%</span>
            </div>
            <div className="mt-3 rounded-md bg-[#FFFAF0] px-3 py-2 text-[10px] leading-relaxed text-text">
              {vehicle.reason}
            </div>
          </div>
        </StepCard>
      </div>
    </div>
  );
}

function StepCard({
  index,
  label,
  description,
  visible,
  accentColor,
  wide = false,
  children,
}: {
  index: number;
  label: string;
  description: string;
  visible: boolean;
  accentColor: "blue" | "red" | "green" | "purple" | "gold";
  wide?: boolean;
  children: React.ReactNode;
}) {
  const colors = {
    blue: "border-blue-500",
    red: "border-red-500",
    green: "border-green-500",
    purple: "border-purple-500",
    gold: "border-[#B8920C]",
  };

  const bgColors = {
    blue: "bg-blue-50",
    red: "bg-red-50",
    green: "bg-green-50",
    purple: "bg-purple-50",
    gold: "bg-[#FFFAF0]",
  };

  return (
    <div
      className={`flex-1 max-w-[220px] rounded-lg border-2 bg-white shadow-sm transition-all duration-500 ${
        colors[accentColor]
      } ${visible ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"}`}
      style={{
        minWidth: wide ? "220px" : "160px",
        minHeight: "200px",
      }}
    >
      <div className={`rounded-t-md px-3 py-2 ${bgColors[accentColor]}`}>
        <div className="text-[10px] font-semibold uppercase tracking-wide text-text-muted">
          Step {index + 1}
        </div>
        <div className="mt-0.5 text-xs font-bold text-navy">{label}</div>
      </div>
      <div className="p-3">
        <p className="mb-3 text-[10px] leading-relaxed text-text-muted">{description}</p>
        {children}
      </div>
    </div>
  );
}

function Arrow() {
  return (
    <div className="flex flex-shrink-0 items-center" style={{ width: "30px", paddingTop: "80px" }}>
      <svg width="30" height="20" viewBox="0 0 30 20" fill="none" className="text-[#CBD5E1]">
        <path
          d="M0 10 L24 10 M18 3 L24 10 L18 17"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}
