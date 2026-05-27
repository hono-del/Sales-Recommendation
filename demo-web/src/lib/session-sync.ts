import { api } from "@/lib/api-client";
import { useDemoStore } from "@/stores/demoStore";

export type StoredAnswer = {
  question_index: number;
  question_id: string;
  answer_key: string;
};

/** サーバー上のセッションを確認し、無ければ再作成して回答を再送する */
export async function ensureSessionSynced(): Promise<string> {
  const state = useDemoStore.getState();
  const answers = state.answers;

  if (!state.sessionId) {
    const sess = await api.createSession();
    useDemoStore.getState().setSessionId(sess.session_id);
    return syncAnswers(sess.session_id, answers);
  }

  try {
    const existing = await api.getSession(state.sessionId);
    if (existing.answers_count >= 4 || answers.length >= 4) {
      return await syncAnswers(state.sessionId, answers);
    }
    if (answers.length > 0) {
      return await syncAnswers(state.sessionId, answers);
    }
    return state.sessionId;
  } catch {
    const sess = await api.createSession();
    useDemoStore.getState().setSessionId(sess.session_id);
    return syncAnswers(sess.session_id, answers);
  }
}

async function syncAnswers(
  sessionId: string,
  answers: StoredAnswer[],
): Promise<string> {
  for (const a of answers) {
    try {
      const res = await api.postAnswer(sessionId, a);
      useDemoStore.getState().setProfile(res.profile, res.mapped_needs);
    } catch {
      /* 個別失敗は続行 */
    }
  }
  return sessionId;
}
