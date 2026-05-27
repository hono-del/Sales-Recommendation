"use client";

import { useEffect, useState } from "react";
import { NARRATION_MESSAGES } from "@/lib/graph-animation";

const ROTATE_MS = 5000;

type Props = {
  messages?: string[];
  active?: boolean;
};

export function NarrationBar({
  messages = NARRATION_MESSAGES,
  active = true,
}: Props) {
  const [index, setIndex] = useState(0);
  const [fade, setFade] = useState(true);

  useEffect(() => {
    if (!active || messages.length <= 1) return;
    const id = setInterval(() => {
      setFade(false);
      setTimeout(() => {
        setIndex((i) => (i + 1) % messages.length);
        setFade(true);
      }, 280);
    }, ROTATE_MS);
    return () => clearInterval(id);
  }, [active, messages.length]);

  return (
    <div
      className="rounded-md border border-border px-4 py-3 text-center text-sm text-text-muted"
      style={{ background: "var(--color-surface)" }}
      role="status"
      aria-live="polite"
    >
      <p
        style={{
          opacity: fade ? 1 : 0,
          transition: "opacity 0.28s ease",
          minHeight: "1.25rem",
        }}
      >
        {messages[index % messages.length]}
      </p>
    </div>
  );
}
