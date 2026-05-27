"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useDemoStore } from "@/stores/demoStore";
import ProfileInputClient from "@/components/demo/ProfileInputClient";

export default function ProfileInputPage() {
  const router = useRouter();
  const sessionId = useDemoStore((state) => state.sessionId);

  useEffect(() => {
    if (!sessionId) {
      router.replace("/demo/opening");
    }
  }, [sessionId, router]);

  if (!sessionId) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-text-muted">リダイレクト中...</p>
      </div>
    );
  }

  return <ProfileInputClient sessionId={sessionId} />;
}
