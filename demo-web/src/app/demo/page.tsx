"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function DemoPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/demo/opening");
  }, [router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-text-muted">リダイレクト中...</p>
    </div>
  );
}
