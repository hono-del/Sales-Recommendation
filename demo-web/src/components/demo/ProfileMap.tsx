import type { ProfileScores } from "@/lib/api-client";

const AXES: { key: keyof ProfileScores; label: string }[] = [
  { key: "score_safety", label: "安心" },
  { key: "score_family", label: "家族" },
  { key: "score_efficiency", label: "効率" },
  { key: "score_enjoyment", label: "楽しさ" },
  { key: "score_adventure", label: "冒険" },
];

type Props = {
  profile: ProfileScores | null;
};

export function ProfileMap({ profile }: Props) {
  if (!profile) {
    return (
      <div className="rounded-md border border-border bg-surface p-6">
        <h2 className="text-lg text-navy">あなたの価値観</h2>
        <p className="mt-4 text-sm text-text-muted">回答すると表示されます</p>
      </div>
    );
  }

  return (
    <div className="rounded-md border border-border bg-surface p-6 shadow-sm">
      <h2 className="text-lg font-medium text-navy">あなたの価値観</h2>
      <ul className="mt-6 space-y-4">
        {AXES.map(({ key, label }) => {
          const value = Math.round(profile[key]);
          return (
            <li key={key}>
              <div className="mb-1 flex justify-between text-sm">
                <span className="text-text">{label}</span>
                <span className="text-text-muted">{value}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-border">
                <div
                  className="h-full rounded-full bg-navy transition-all duration-300 ease-out"
                  style={{ width: `${value}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
