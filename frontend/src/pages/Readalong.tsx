import { useCallback, useEffect, useState } from "react";
import { evaluateReadalong, fetchStoryPage, nextReadalong } from "../api";
import type { Child, ReadalongResult, StorySummary } from "../types";
import { listenOnce, speak, sttSupported } from "../speech";

interface StoryState {
  story: StorySummary;
  page_index: number;
  en: string;
  cn: string;
  words: string[];
  due_words: string[];
}

const CHAR_EMOJI: Record<string, string> = {
  maisy: "🐭",
  peppa: "🐷",
  chase: "🐶",
  penelope: "🐨",
};

/** 跟读练习页（M03.F02.I03）：句子卡 + TTS 示范 + STT 跟读 + 逐词反馈。 */
export default function Readalong({ child }: { child: Child }) {
  const [state, setState] = useState<StoryState | null>(null);
  const [result, setResult] = useState<ReadalongResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(
    async (storyId?: string) => {
      setBusy(true);
      setError("");
      setResult(null);
      try {
        const next = await nextReadalong(child.id, storyId);
        setState({
          story: next.story,
          page_index: next.page_index,
          en: next.page.en,
          cn: next.page.cn,
          words: next.page.words,
          due_words: next.due_words,
        });
      } catch (e) {
        setError(e instanceof Error ? e.message : "取故事失败");
      } finally {
        setBusy(false);
      }
    },
    [child.id],
  );

  useEffect(() => {
    load();
  }, [load]);

  async function gotoPage(delta: number) {
    if (!state) return;
    const target = state.page_index + delta;
    if (target < 0) return;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const d = await fetchStoryPage(state.story.id, target);
      setState({ ...state, page_index: d.page_index, en: d.page.en, cn: d.page.cn, words: d.page.words });
    } catch {
      setError("这一页不存在");
    } finally {
      setBusy(false);
    }
  }

  async function handleRead() {
    if (!state || listening) return;
    setListening(true);
    setError("");
    try {
      const transcript = await listenOnce();
      setBusy(true);
      const r = await evaluateReadalong(child.id, state.story.id, state.page_index, transcript);
      setResult(r);
      speak(r.encouragement_en);
    } catch (e) {
      setError(e instanceof Error ? e.message : "评价失败，再试一次");
    } finally {
      setListening(false);
      setBusy(false);
    }
  }

  if (!state) {
    return <div className="empty-note">{error || "挑故事中…"}</div>;
  }

  const last = result ? result.results[result.results.length - 1] : undefined;

  return (
    <div>
      <div className="story-head">
        <span className="cover" aria-hidden>{CHAR_EMOJI[state.story.character_id] ?? "📕"}</span>
        <div>
          <div className="t-en">{state.story.title_en}</div>
          <div className="t-cn">
            {state.story.title_cn} · 第 {state.page_index + 1}/{state.story.total_pages} 页
          </div>
        </div>
      </div>

      <div className="crayon-card sentence-card">
        <div className="en-line">{state.en}</div>
        <div className="cn-line">{state.cn}</div>
        <div className="target-words">
          {state.words.map((w) => (
            <span key={w} className={`word-sticker ${state.due_words.includes(w) ? "ws-growing" : "ws-learning"}`}>
              {w}
            </span>
        ))}
        </div>

        {result && (
          <>
            <div className="feedback-list">
              {result.results.map((r) => (
                <span key={r.word} className={r.ok ? "pill-ok" : "pill-miss"}>
                  {r.ok ? "✓" : "✗"} {r.word}
                </span>
              ))}
            </div>
            <div className="encourage">
              <div className="en">{result.encouragement_en}</div>
              <div className="cn">{result.encouragement_cn}</div>
              {result.tip_cn && <div className="tip">{result.tip_cn}</div>}
              {last && !last.ok && <div className="heard-line">听到的是：<b>{last.heard || "…"}</b></div>}
            </div>
          </>
        )}

        {error && <p className="empty-note" role="alert">{error}</p>}

        <div className="action-row">
          <button className="btn ghost" onClick={() => speak(state.en)} aria-label="听示范">
            🔊 听示范
          </button>
          <button
            className={`btn mic-btn ${listening ? "listening" : ""}`}
            onClick={handleRead}
            disabled={busy}
            aria-label="跟读这句"
          >
            🎤 {listening ? "在听…" : "我来读"}
          </button>
        </div>
        {!sttSupported() && (
          <p className="empty-note">这个浏览器不支持麦克风识别，换 Chrome/Edge 体验跟读。</p>
        )}
        <div className="page-dots">
          {state.page_index > 0 && (
            <button className="say-btn" onClick={() => gotoPage(-1)}>← 上一页</button>
          )}
          {"　"}
          {state.page_index + 1 < state.story.total_pages && (
            <button className="say-btn" onClick={() => gotoPage(1)}>下一页 →</button>
          )}
        </div>
      </div>
    </div>
  );
}
