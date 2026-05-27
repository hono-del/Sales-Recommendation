import type { Question, QuestionChoice } from "@/types/demo";

type Props = {
  question: Question;
  currentIndex: number;
  total: number;
  selectedKey: string | null;
  onSelect: (choice: QuestionChoice) => void;
  onNext: () => void;
  loading?: boolean;
};

export function QuestionCard({
  question,
  currentIndex,
  total,
  selectedKey,
  onSelect,
  onNext,
  loading,
}: Props) {
  return (
    <div className="rounded-md border border-border bg-surface p-8 shadow-sm">
      <p className="text-sm text-text-muted">
        Q {currentIndex} / {total}
      </p>
      <h2 className="mt-2 text-2xl font-light text-navy">{question.text}</h2>
      <div className="mt-8 flex flex-col gap-3">
        {question.choices.map((choice) => (
          <button
            key={choice.key}
            type="button"
            disabled={loading}
            onClick={() => onSelect(choice)}
            className={`rounded-md border px-4 py-3 text-left text-base transition-colors ${
              selectedKey === choice.key
                ? "border-navy bg-navy/5 text-navy"
                : "border-border bg-bg hover:border-navy-light hover:bg-surface"
            }`}
          >
            {choice.label}
          </button>
        ))}
      </div>
      {selectedKey && (
        <button
          type="button"
          onClick={onNext}
          disabled={loading}
          className="mt-8 w-full rounded-md bg-navy py-3 text-white hover:bg-navy-light disabled:opacity-50"
        >
          {currentIndex < total ? "次の質問 →" : "AI Delegation へ →"}
        </button>
      )}
    </div>
  );
}
