"use client";

import Link from "next/link";
import { useDemoStore } from "@/stores/demoStore";
import { PrimaryButton } from "./PrimaryButton";

const JOURNEY = [
  { step: "選ぶ", desc: "納得の一台を", icon: "🎯" },
  { step: "乗る", desc: "期待を超える体験", icon: "🚗" },
  { step: "使いこなす", desc: "AXIS でサポート", icon: "📱" },
  { step: "生活が整う", desc: "継続的な関係", icon: "✨" },
];

export function ClosingClient() {
  const reset = useDemoStore((s) => s.reset);

  return (
    <main className="mx-auto max-w-4xl px-6 py-16">
      <div className="text-center">
        <h1 className="text-4xl font-light text-navy">購入後も、伴走し続ける</h1>
        <p className="mt-4 text-lg text-text-muted">
          Decision Intelligence は「売って終わり」ではなく、
          <br />
          選ぶ → 乗る → 使いこなす → 生活が整う までをつなぎます。
        </p>
      </div>
      <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {JOURNEY.map((item, i) => (
          <div
            key={item.step}
            className="relative rounded-lg border border-border bg-surface p-6 text-center"
          >
            <div className="absolute right-4 top-4 text-2xl opacity-20">{item.icon}</div>
            <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-navy/10 text-xl mx-auto">
              {i + 1}
            </div>
            <p className="text-lg font-medium text-navy">{item.step}</p>
            <p className="mt-1 text-sm text-text-muted">{item.desc}</p>
          </div>
        ))}
      </div>
      
      <div className="mt-12 rounded-lg border border-gold/30 bg-surface p-8">
        <h2 className="text-center text-xl font-medium text-navy">AXIS による一気通貫支援</h2>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <div className="text-center">
            <p className="text-3xl">🔔</p>
            <p className="mt-2 text-sm font-medium text-navy">メンテナンス通知</p>
            <p className="mt-1 text-xs text-text-muted">適切なタイミングで案内</p>
          </div>
          <div className="text-center">
            <p className="text-3xl">📊</p>
            <p className="mt-2 text-sm font-medium text-navy">利用状況分析</p>
            <p className="mt-1 text-xs text-text-muted">最適な提案のため</p>
          </div>
          <div className="text-center">
            <p className="text-3xl">🔄</p>
            <p className="mt-2 text-sm font-medium text-navy">次回購入支援</p>
            <p className="mt-1 text-xs text-text-muted">生活変化に寄り添う</p>
          </div>
        </div>
      </div>
      <div className="mt-12 rounded-md bg-bg p-6 text-center">
        <p className="text-sm leading-relaxed text-text">
          <strong className="text-navy">本デモは PoC です。</strong>
          <br />
          本番では AXIS（購入後体験プラットフォーム）と連携し、
          <br />
          オーナー体験・メンテナンス・リコール・次回購入まで一気通貫で支援します。
        </p>
      </div>
      <div className="mt-10 flex flex-col items-center gap-4">
        <PrimaryButton
          onClick={() => {
            reset();
            window.location.href = "/demo/opening";
          }}
        >
          もう一度体験する
        </PrimaryButton>
        <Link
          href="/demo/opening"
          onClick={() => reset()}
          style={{ fontSize: 14, color: "var(--color-text-muted)", textDecoration: "underline" }}
        >
          最初からやり直す
        </Link>
      </div>
    </main>
  );
}
