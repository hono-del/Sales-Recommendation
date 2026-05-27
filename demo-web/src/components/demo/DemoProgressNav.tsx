import { demoScreens } from "@/lib/design-tokens";

type Props = {
  currentStep: number;
};

export function DemoProgressNav({ currentStep }: Props) {
  const total = demoScreens.length;
  const pct = Math.round((currentStep / total) * 100);

  return (
    <header className="border-b border-border bg-surface px-6 py-3">
      <div className="mx-auto flex max-w-[1280px] items-center gap-4">
        <span className="text-sm text-text-muted">
          Step {currentStep}/{total}
        </span>
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-border">
          <div
            className="h-full bg-navy transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </header>
  );
}
