const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type ProfileScores = {
  score_safety: number;
  score_family: number;
  score_efficiency: number;
  score_enjoyment: number;
  score_adventure: number;
};

export type SessionCreateResponse = {
  session_id: string;
  created_at: string;
  status: string;
};

export type AnswerResponse = {
  session_id: string;
  profile: ProfileScores;
  mapped_needs: string[];
  mapped_capabilities: string[];
  detected_loads: string[];
};

export type HealthResponse = {
  status: string;
  neo4j: "connected" | "unavailable";
};

export type QuestionMaster = {
  version: string;
  questions: {
    index: number;
    id: string;
    text: string;
    choices: { key: string; label: string }[];
  }[];
};

export type RecommendResponse = {
  session_id: string;
  demo_fallback: boolean;
  recommendations: {
    model: string;
    score: number;
    reason: string;
    archetype: string;
    similar_consumers?: string[];
  }[];
  excluded: { model: string; reason: string }[];
  ui_needs?: string[];
};

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

const DEFAULT_TIMEOUT_MS = 8000;

async function request<T>(
  path: string,
  init?: RequestInit,
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch (err) {
    clearTimeout(timer);
    if (err instanceof Error && err.name === "AbortError") {
      throw new ApiError(
        `API がタイムアウトしました（${timeoutMs / 1000}秒）。FastAPI (port 8000) を確認してください。`,
        0,
      );
    }
    throw new ApiError(
      `API に接続できません（${API_URL}）。FastAPI が起動しているか確認してください。`,
      0,
    );
  } finally {
    clearTimeout(timer);
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const msg =
      typeof err.detail === "string"
        ? err.detail
        : Array.isArray(err.detail)
          ? err.detail.map((d: { msg?: string }) => d.msg).join(", ")
          : `API error ${res.status}`;
    throw new ApiError(msg, res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthResponse>("/health", undefined, 3000),

  createSession: () =>
    request<SessionCreateResponse>("/api/demo/sessions", {
      method: "POST",
      body: "{}",
    }),

  getSession: (sessionId: string) =>
    request<{
      session_id: string;
      status: string;
      answers_count: number;
      profile: unknown;
    }>(`/api/demo/sessions/${sessionId}`),

  postAnswer: (
    sessionId: string,
    body: {
      question_index: number;
      question_id: string;
      answer_key: string;
    },
  ) =>
    request<AnswerResponse>(`/api/demo/sessions/${sessionId}/answers`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  setDelegation: (sessionId: string, delegation_level: string) =>
    request<{ session_id: string; delegation_level: string; message: string }>(
      `/api/demo/sessions/${sessionId}/delegation`,
      {
        method: "PATCH",
        body: JSON.stringify({ delegation_level }),
      },
    ),

  getQuestions: () => request<QuestionMaster>("/api/demo/questions"),

  postRecommend: (sessionId: string) =>
    request<RecommendResponse>(`/api/demo/sessions/${sessionId}/recommend`, {
      method: "POST",
      body: "{}",
    }),

  getFallbackRecommend: () =>
    request<RecommendResponse>("/api/demo/fallback/recommend"),

  getGraphPath: (sessionId: string, topModel?: string) => {
    const q = topModel ? `?top_model=${encodeURIComponent(topModel)}` : "";
    return request<Record<string, unknown>>(
      `/api/demo/sessions/${sessionId}/graph-path${q}`,
    );
  },

  postDealerTalk: (
    sessionId: string,
    body: { top_model: string; delegation_level: string },
  ) =>
    request<{
      insight: {
        customer_type: string;
        scenes: string[];
        anxieties: string[];
        values: string[];
      };
      talk_script: string;
      generated_by: string;
    }>(`/api/demo/sessions/${sessionId}/dealer-talk`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  postEvent: (
    sessionId: string,
    body: {
      screen_id: string;
      event_type: string;
      payload?: Record<string, unknown>;
    },
  ) =>
    request<{ id: string; created_at: string }>(
      `/api/demo/sessions/${sessionId}/events`,
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    ).catch(() => ({ id: "", created_at: "" })),
};
