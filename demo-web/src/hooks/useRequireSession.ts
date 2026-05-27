"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useDemoStore } from "@/stores/demoStore";

export function useRequireSession(redirectTo = "/demo/opening") {
  const router = useRouter();
  const sessionId = useDemoStore((s) => s.sessionId);

  useEffect(() => {
    if (!sessionId) {
      router.replace(redirectTo);
    }
  }, [sessionId, router, redirectTo]);

  return sessionId;
}
