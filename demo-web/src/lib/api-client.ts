const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 
  (typeof window !== 'undefined' && window.location.hostname === 'localhost' 
    ? "http://127.0.0.1:8000" 
    : "https://sales-recommendation.onrender.com");

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

export type ProfileInputRequest = {
  family_size: number;
  budget_range: string;
};

export type ProfileInputResponse = {
  session_id: string;
  status: string;
  family_size: number;
  budget_min: number;
  budget_max: number;
};

export type KgCatalogItem = {
  name: string;
  label?: string;
  group?: string;
  category?: string;
  selected: boolean;
  source?: string;
  source_load?: string;
  source_axis?: string;
  weight?: number;
  linked_needs?: string[];
  capabilities?: string[];
};

export type KgCatalogResponse = {
  kind: string;
  total: number;
  selected_count: number;
  groups?: string[];
  categories?: string[];
  vehicle_name?: string;
  items: KgCatalogItem[];
};

export type AnswerResponse = {
  session_id: string;
  profile: ProfileScores;
  mapped_needs: string[];
  kg_needs?: KgCatalogItem[];
  mapped_capabilities: string[];
  detected_loads: string[];
  decision_style?: string;
  decision_style_label?: string;
  decision_style_description?: string;
  decision_style_scores?: Record<string, number>;
  decision_style_confidence?: number;
  decision_style_secondary?: string;
  decision_style_secondary_label?: string;
  decision_style_is_mixed?: boolean;
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

  /**
   * Renderのウェイクアップを待機しながらヘルスチェック
   * @param onProgress 進捗コールバック (attempt, maxAttempts, elapsedSeconds)
   * @param maxAttempts 最大リトライ回数
   * @returns ヘルスチェック成功時true、失敗時false
   */
  async waitForApiReady(
    onProgress?: (attempt: number, maxAttempts: number, elapsedSeconds: number) => void,
    maxAttempts: number = 20
  ): Promise<boolean> {
    const startTime = Date.now();
    
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        const elapsedSeconds = Math.floor((Date.now() - startTime) / 1000);
        onProgress?.(attempt, maxAttempts, elapsedSeconds);
        
        await this.health();
        return true; // 成功
      } catch {
        // 最後の試行で失敗した場合
        if (attempt === maxAttempts) {
          return false;
        }
        
        // 次の試行まで待機（段階的に間隔を増やす）
        const waitTime = attempt <= 3 ? 2000 : attempt <= 10 ? 3000 : 5000;
        await new Promise(resolve => setTimeout(resolve, waitTime));
      }
    }
    
    return false;
  },

  createSession: () =>
    request<SessionCreateResponse>(
      "/api/demo/sessions",
      {
        method: "POST",
        body: "{}",
      },
      15000,
    ),

  getSession: (sessionId: string) =>
    request<{
      session_id: string;
      status: string;
      answers_count: number;
      answers?: Array<{
        question_index: number;
        question_id: string;
        answer_key: string;
      }>;
      profile: unknown;
    }>(`/api/demo/sessions/${sessionId}`, undefined, 15000),

  postProfileInput: (sessionId: string, body: ProfileInputRequest) =>
    request<ProfileInputResponse>(
      `/api/demo/sessions/${sessionId}/profile`,
      {
        method: "POST",
        body: JSON.stringify(body),
      },
      15000,
    ),

  postAnswer: (
    sessionId: string,
    body: {
      question_index: number;
      question_id: string;
      answer_key: string;
    },
  ) =>
    request<AnswerResponse>(
      `/api/demo/sessions/${sessionId}/answers`,
      {
        method: "POST",
        body: JSON.stringify(body),
      },
      15000,
    ),

  setDelegation: (sessionId: string, delegation_level: string) =>
    request<{ session_id: string; delegation_level: string; message: string }>(
      `/api/demo/sessions/${sessionId}/delegation`,
      {
        method: "PATCH",
        body: JSON.stringify({ delegation_level }),
      },
    ),

  getQuestions: () => request<QuestionMaster>("/api/demo/questions"),

  getServiceQuestions: () => request<QuestionMaster>("/api/demo/service-questions"),

  postRecommend: (sessionId: string) =>
    request<RecommendResponse>(
      `/api/demo/sessions/${sessionId}/recommend`,
      {
        method: "POST",
        body: "{}",
      },
      15000, // Claude API呼び出しを含むため15秒
    ),

  getFallbackRecommend: () =>
    request<RecommendResponse>("/api/demo/fallback/recommend"),

  getGraphPath: (sessionId: string, topModel?: string) => {
    const q = topModel ? `?top_model=${encodeURIComponent(topModel)}` : "";
    return request<Record<string, unknown>>(
      `/api/demo/sessions/${sessionId}/graph-path${q}`,
      undefined,
      30000, // graph-path は重い処理のため30秒に延長
    );
  },

  getKgNeedsCatalog: (sessionId: string) =>
    request<KgCatalogResponse>(
      `/api/demo/sessions/${sessionId}/kg-catalog/needs`,
      undefined,
      10000,
    ),

  getKgFeaturesCatalog: (sessionId: string, topModel?: string) => {
    const q = topModel ? `?top_model=${encodeURIComponent(topModel)}` : "";
    return request<KgCatalogResponse>(
      `/api/demo/sessions/${sessionId}/kg-catalog/technical-features${q}`,
      undefined,
      15000,
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

  getServiceRecommendations: (sessionId: string) =>
    request<{
      services: Array<{
        id: string;
        title: string;
        one_liner: string;
        direction: string;
        domain: string;
        score: number;
        matched_needs: string[];
        matched_loads: string[];
        value_alignment: number;
        pitch: string;
        need_rationale: string;
      }>;
      fallback: boolean;
    }>(
      `/api/demo/sessions/${sessionId}/services`,
      undefined,
      10000,
    ),

  getNeedMapping: () =>
    request<{
      version: string;
      description: string;
      answer_to_needs: Record<string, Record<string, string[]>>;
      need_to_capabilities: Record<string, string>;
      profile_to_ui_needs: Record<string, string>;
      capability_labels_ja: Record<string, string>;
    }>("/api/demo/need-mapping", undefined, 5000),

  getMasterData: () =>
    request<{
      all_needs: string[];
      all_loads: string[];
      all_services: Array<{
        id: string;
        title: string;
        one_liner: string;
        direction: string;
        domain: string;
        lifecycle: string;
        pitch_template: string;
        need_rationale: string;
        load_labels: string[];
        value_axes: string[];
      }>;
    }>("/api/demo/master-data", undefined, 5000),

  postServiceFeedback: (
    sessionId: string,
    body: {
      service_id: string;
      service_rank: number;
      service_score: number;
      feedback_value: string;
      matched_needs: string[];
      matched_loads: string[];
      value_alignment: number;
    },
  ) =>
    request<{ message: string }>(
      `/api/demo/sessions/${sessionId}/service-feedback`,
      {
        method: "POST",
        body: JSON.stringify(body),
      },
      5000,
    ),

  logSessionAnalytics: (sessionId: string) =>
    request<{ message: string; log_entry: unknown }>(
      `/api/demo/sessions/${sessionId}/log-analytics`,
      {
        method: "POST",
      },
      15000,
    ),

  getSimilarProfiles: (sessionId: string) =>
    request<{
      total_users: number;
      similar_users: number;
      similarity_rate: number;
    }>(`/api/demo/sessions/${sessionId}/similar-profiles`, undefined, 5000),

  getAnalyticsLogs: () =>
    request<{
      total: number;
      logs: Array<{
        session_id: string;
        logged_at: string;
        created_at: string;
        status: string;
        value_profile: {
          safety: number;
          family: number;
          efficiency: number;
          enjoyment: number;
          adventure: number;
        };
        mapped_needs: string[];
        detected_loads: Array<{
          name: string;
          description: string;
          related_values: string[];
        }>;
        recommended_services: Array<{
          service_id: string;
          title: string;
          rank: number;
          score: number;
          matched_needs: string[];
          matched_loads: string[];
        }>;
        service_feedbacks: Array<{
          service_id: string;
          service_rank: number;
          feedback_value: string;
          timestamp: string;
        }>;
        answers_count: number;
      }>;
    }>("/api/demo/analytics/logs", undefined, 10000),
};
