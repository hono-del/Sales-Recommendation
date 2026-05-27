type Level = "guide" | "co_pilot" | "auto";

const LEVELS: {
  id: Level;
  title: string;
  description: string;
  badge?: string;
}[] = [
  {
    id: "guide",
    title: "候補だけほしい",
    description: "AIは選択肢を整理するだけ。決めるのはあなた。",
  },
  {
    id: "co_pilot",
    title: "一緒に考えてほしい",
    description: "理由を見ながら、納得いくまで伴走します。",
    badge: "推奨",
  },
  {
    id: "auto",
    title: "最適案を提案してほしい",
    description: "結論と根拠をコンパクトに提示します。",
  },
];

type Props = {
  selected: Level;
  onSelect: (level: Level) => void;
};

export function DelegationSelector({ selected, onSelect }: Props) {
  return (
    <div className="mt-10 grid gap-4 md:grid-cols-3">
      {LEVELS.map((level) => (
        <button
          key={level.id}
          type="button"
          onClick={() => onSelect(level.id)}
          className={`relative rounded-md border bg-surface p-6 text-left transition-all ${
            selected === level.id
              ? "scale-[1.02] border-2 border-navy shadow-md"
              : "border-border hover:border-navy-light hover:shadow-sm"
          }`}
        >
          {level.badge && (
            <span className="absolute right-3 top-3 rounded bg-gold/20 px-2 py-0.5 text-xs font-medium text-gold">
              {level.badge}
            </span>
          )}
          <h3 className="text-lg text-navy">{level.title}</h3>
          <p className="mt-2 text-sm leading-relaxed text-text-muted">
            {level.description}
          </p>
        </button>
      ))}
    </div>
  );
}
