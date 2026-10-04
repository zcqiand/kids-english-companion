import { useCallback, useEffect, useState } from "react";
import { evaluatePronunciation, fetchPronunciationWords } from "../api";
import type { Child, PronunciationResult, WordCard } from "../types";
import { listenOnce, speak } from "../speech";

const STATUS_CN_CLASS: Record<string, string> = {
  learning: "st-learning",
  growing: "st-growing",
  mastered: "st-mastered",
};
const STATUS_LABEL: Record<string, string> = {
  learning: "学习中",
  growing: "巩固中",
  mastered: "已掌握",
};

/** 发音练习页（M04.F01.I03）：词卡 + 示范朗读 + 录音评价。 */
export default function Pronunciation({ child }: { child: Child }) {
  const [words, setWords] = useState<WordCard[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [result, setResult] = useState<PronunciationResult | null>(null);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const d = await fetchPronunciationWords(child.id);
      setWords(d.words);
      setActiveId(d.words[0]?.word_id ?? null);
      setResult(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "取词卡失败");
    }
  }, [child.id]);

  useEffect(() => {
    load();
  }, [load]);

  const active = words.find((w) => w.word_id === activeId) ?? null;

  async function handleTry() {
    if (!active || listening) return;
    setListening(true);
    setError("");
    try {
      const transcript = await listenOnce();
      const r = await evaluatePronunciation(child.id, active.text, transcript);
      setResult(r);
      speak(r.correct ? r.encouragement_en || "Great job!" : "Nice try!");
      load(); // 状态变了 → 重取词卡（到期/薄弱会重排）
    } catch (e) {
      setError(e instanceof Error ? e.message : "没听清，再试一次");
    } finally {
      setListening(false);
    }
  }

  return (
    <div>
      <h1 className="page-title">今天练哪几个？</h1>
      <p className="page-sub">黄色和蓝色的词最需要你。先听，再大声说！</p>

      <div className="word-grid">
        {words.map((w) => (
          <button
            key={w.word_id}
            className={`word-card ${w.word_id === activeId ? "active" : ""}`}
            onClick={() => {
              setActiveId(w.word_id);
              setResult(null);
              speak(w.text);
            }}
          >
            <div className="w">{w.text}</div>
            <div className="ph">{w.phonetic}</div>
            <div className="cn">{w.meaning_cn}</div>
            <span className={`status-chip ${STATUS_CN_CLASS[w.status] ?? "st-learning"}`}>
              {STATUS_LABEL[w.status] ?? w.status}
            </span>
          </button>
        ))}
      </div>

      {active && (
        <div className="crayon-card" style={{ marginTop: 16 }}>
          <div className="sentence-card" style={{ padding: "8px 0 0" }}>
            <div className="en-line">{active.text}</div>
            <div className="cn-line">
              {active.meaning_cn} {active.phonetic}
            </div>
          </div>

          {result && (
            <div className="encourage">
              <div className="en" style={{ color: result.correct ? "var(--grass)" : "var(--sun)" }}>
                {result.correct ? "🎉 " : "💪 "}
                {result.correct ? result.encouragement_en || "Great job!" : "Nice try!"}
              </div>
              <div className="cn">{result.correct ? result.encouragement_cn : "再试一次，你能行的！"}</div>
              {result.tip_cn && <div className="tip">{result.tip_cn}</div>}
              <div className="heard-line">
                听到的音：<b>{result.heard || "…"}</b> · 现在是「{STATUS_LABEL[result.status] ?? result.status}」
              </div>
            </div>
          )}

          {error && <p className="empty-note" role="alert">{error}</p>}

          <div className="action-row">
            <button className="btn ghost" onClick={() => speak(active.text)} aria-label="听示范">
              🔊 听示范
            </button>
            <button
              className={`btn mic-btn ${listening ? "listening" : ""}`}
              onClick={handleTry}
              disabled={listening}
              aria-label="跟读这个词"
            >
              🎤 {listening ? "在听…" : "我来说"}
            </button>
          </div>
        </div>
      )}

      {words.length === 0 && !error && <div className="empty-note">词卡准备好啦，马上回来。</div>}
    </div>
  );
}
