/** API 封装：全部同源相对路径（vite proxy → 8801），无绝对 baseURL。 */
import type {
  Child,
  Character,
  PronunciationResult,
  ReadalongNext,
  ReadalongResult,
  StoryPage,
  StorySummary,
  WordCard,
} from "./types";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    const detail = await res
      .json()
      .then((d) => d?.detail)
      .catch(() => null);
    throw new Error(detail || `请求失败 (${res.status})`);
  }
  return res.json();
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res
      .json()
      .then((d) => d?.detail)
      .catch(() => null);
    throw new Error(detail || `请求失败 (${res.status})`);
  }
  return res.json();
}

// ---- 元数据 ----

export function fetchCharacters(): Promise<{ characters: Character[] }> {
  return getJSON("/api/characters");
}

export function fetchStories(): Promise<{ stories: StorySummary[] }> {
  return getJSON("/api/stories");
}

// ---- 档案 ----

export function fetchChildren(): Promise<{ children: Child[] }> {
  return getJSON("/api/children");
}

export function createChild(name: string, age: number, characterId: string): Promise<{ child: Child }> {
  return postJSON("/api/children", { name, age, character_id: characterId });
}

export interface Dashboard {
  words: Array<Record<string, unknown> & { text: string; status: string; weak: boolean }>;
  due_today: string[];
  weak: string[];
  streak: number;
  stats: { 学习中: number; 巩固中: number; 已掌握: number; total_known: number };
  recent_events: Array<{
    id: number;
    word: string;
    kind: string;
    success: number;
    detail: string;
    happened_at: string;
  }>;
  activity: Record<string, number>;
}

export function fetchDashboard(childId: string): Promise<{ dashboard: Dashboard }> {
  return getJSON(`/api/children/${childId}/progress`);
}

// ---- 对话 SSE ----

export interface ChatEvent {
  type: string;
  [k: string]: unknown;
}

/** POST + SSE 流式解析。onEvent 逐事件回调；服务端 done/error 结束。 */
export async function streamChat(
  childId: string,
  text: string,
  sessionId: string | null,
  onEvent: (ev: ChatEvent) => void,
): Promise<void> {
  const res = await fetch(`/api/children/${childId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, session_id: sessionId }),
  });
  if (!res.ok || !res.body) {
    throw new Error(`对话请求失败 (${res.status})`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const line = block.trim();
      if (!line.startsWith("data: ")) continue;
      try {
        onEvent(JSON.parse(line.slice(6)));
      } catch {
        // 半个 JSON 块，忽略
      }
    }
  }
}

export function endSession(childId: string, sessionId: string): Promise<{ ok: boolean; streak_days?: number }> {
  return postJSON(`/api/sessions/${sessionId}/end`, { child_id: childId, notes: "家长手动结束" });
}

// ---- 跟读 ----

export function nextReadalong(childId: string, storyId?: string): Promise<ReadalongNext> {
  const q = storyId ? `?story_id=${encodeURIComponent(storyId)}` : "";
  return getJSON(`/api/children/${childId}/readalong/next${q}`);
}

export function fetchStoryPage(storyId: string, pageIndex: number): Promise<{
  story: StorySummary;
  page_index: number;
  page: StoryPage;
}> {
  return getJSON(`/api/stories/${storyId}/pages/${pageIndex}`);
}

export function evaluateReadalong(
  childId: string,
  storyId: string,
  pageIndex: number,
  transcript: string,
): Promise<ReadalongResult> {
  return postJSON(`/api/children/${childId}/readalong/evaluate`, {
    story_id: storyId,
    page_index: pageIndex,
    transcript,
  });
}

// ---- 发音 ----

export function fetchPronunciationWords(childId: string): Promise<{ words: WordCard[] }> {
  return getJSON(`/api/children/${childId}/pronunciation/words`);
}

export function evaluatePronunciation(
  childId: string,
  word: string,
  transcript: string,
): Promise<PronunciationResult> {
  return postJSON(`/api/children/${childId}/pronunciation/evaluate`, { word, transcript });
}
