import { useEffect, useRef, useState } from "react";
import { endSession, streamChat } from "../api";
import type { Character, Child } from "../types";
import { listenOnce, speak, sttSupported, stopSpeaking } from "../speech";

interface Bubble {
  role: "buddy" | "kid";
  text: string;
  stickers: Array<{ word: string; meaning: string; status: string }>;
  speaking?: boolean;
}

const STATUS_CLASS: Record<string, string> = {
  新词: "ws-new",
  学习中: "ws-learning",
  巩固中: "ws-growing",
  已掌握: "ws-mastered",
};

/** 角色对话页（M02）：SSE 流式 + 贴纸高亮 + TTS/STT。 */
export default function Chat({ child }: { child: Child }) {
  const [character, setCharacter] = useState<Character | null>(null);
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [listening, setListening] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const sessionIdRef = useRef<string | null>(null);

  useEffect(() => {
    fetch("/api/characters")
      .then((r) => r.json())
      .then((d) => setCharacter(d.characters.find((c: Character) => c.id === child.character_id) ?? null))
      .catch(() => {});
  }, [child.character_id]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [bubbles, thinking]);

  function push(update: (prev: Bubble[]) => Bubble[]) {
    setBubbles(update);
  }

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || thinking) return;
    stopSpeaking();
    setInput("");
    push((prev) => [...prev, { role: "kid", text: trimmed, stickers: [] }]);
    setThinking(true);
    const buddy: Bubble = { role: "buddy", text: "", stickers: [] };
    push((prev) => [...prev, buddy]);

    try {
      await streamChat(child.id, trimmed, sessionIdRef.current, (ev) => {
        if (ev.type === "session") {
          sessionIdRef.current = String(ev.session_id);
          setSessionId(sessionIdRef.current);
        } else if (ev.type === "delta") {
          const chunk = String(ev.text ?? "");
          push((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.role === "buddy") {
              next[next.length - 1] = { ...last, text: last.text + chunk };
            }
            return next;
          });
        } else if (ev.type === "word_focus") {
          push((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.role === "buddy") {
              next[next.length - 1] = {
                ...last,
                stickers: [
                  ...last.stickers,
                  { word: String(ev.word), meaning: String(ev.meaning), status: String(ev.status) },
                ],
              };
            }
            return next;
          });
        } else if (ev.type === "error") {
          push((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            const friendly = String(ev.message ?? "出了点小状况，再试一次好吗？");
            if (last && last.role === "buddy" && !last.text) {
              next[next.length - 1] = { ...last, text: friendly };
            } else {
              next.push({ role: "buddy", text: friendly, stickers: [] });
            }
            return next;
          });
        }
      });
      // 完成：自动朗读英文部分（第一行），并提供喇叭按钮
      setBubbles((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === "buddy" && last.text) {
          const enLine = last.text.split("\n")[0];
          speak(enLine);
        }
        return prev;
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "网络开小差了，再试一次好吗？";
      push((prev) => [...prev, { role: "buddy", text: msg, stickers: [] }]);
    } finally {
      setThinking(false);
    }
  }

  async function handleMic() {
    if (listening) return;
    setListening(true);
    try {
      const transcript = await listenOnce();
      await send(transcript);
    } catch (e) {
      push((prev) => [...prev, { role: "buddy", text: e instanceof Error ? e.message : "没听清", stickers: [] }]);
    } finally {
      setListening(false);
    }
  }

  async function handleEnd() {
    if (!sessionIdRef.current) return;
    try {
      await endSession(child.id, sessionIdRef.current);
    } catch {
      // 忽略重复结束
    }
    sessionIdRef.current = null;
    setSessionId(null);
    push((prev) => [
      ...prev,
      { role: "buddy", text: "今天玩得开心吗？明天我们继续哦！\n今天玩得开心吗？明天再一起玩！", stickers: [] },
    ]);
  }

  const canMic = sttSupported();

  return (
    <div className="chat-wrap" style={{ display: "flex", flexDirection: "column", flex: 1 }}>
      <div className="chat-scroll" ref={scrollRef}>
        {bubbles.length === 0 && character && (
          <div className="msg-row buddy">
            <span className="avatar" aria-hidden>{character.emoji}</span>
            <div className="stack">
              <div className="bubble">
                {character.greeting_en}{"\n"}{character.greeting_cn}
              </div>
              <button
                className="say-btn"
                onClick={() => speak(character.greeting_en)}
                aria-label="朗读问候语"
              >
                🔊 点我听
              </button>
            </div>
          </div>
        )}
        {bubbles.map((b, i) => (
          <div key={i} className={`msg-row ${b.role === "buddy" ? "buddy" : "kid"}`}>
            {b.role === "buddy" && (
              <span className="avatar" aria-hidden>{character?.emoji ?? "🐾"}</span>
            )}
            <div className="stack">
              <div className="bubble">{b.text || "…"}</div>
              {b.stickers.length > 0 && (
                <div className="feedback-list" style={{ justifyContent: "flex-start", margin: 0 }}>
                  {b.stickers.map((s) => (
                    <span key={s.word} className={`word-sticker ${STATUS_CLASS[s.status] ?? "ws-new"}`}>
                      {s.word}
                      <span className="cn">{s.meaning}</span>
                    </span>
                  ))}
                </div>
              )}
              {b.role === "buddy" && b.text && (
                <button
                  className="say-btn"
                  onClick={() => speak(b.text.split("\n")[0])}
                  aria-label="朗读这句英文"
                >
                  🔊 再听一遍
                </button>
              )}
            </div>
          </div>
        ))}
        {thinking && (
          <div className="msg-row buddy">
            <span className="avatar" aria-hidden>{character?.emoji ?? "🐾"}</span>
            <div className="bubble typing-dot" aria-label="伙伴正在想">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}
      </div>

      <div className="chat-inputbar">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(input)}
          placeholder={canMic ? "说英语，或按下麦克风" : "输入英语句子"}
          aria-label="输入英语"
          disabled={thinking}
        />
        {canMic && (
          <button
            className={`btn mic-btn ${listening ? "listening" : ""}`}
            onClick={handleMic}
            disabled={thinking}
            aria-label={listening ? "正在听…" : "按住说英语"}
          >
            🎤
          </button>
        )}
        <button className="btn" onClick={() => send(input)} disabled={thinking || !input.trim()}>
          发送
        </button>
      </div>
      <div className="end-row">
        <button className="say-btn" onClick={handleEnd} disabled={!sessionId}>
          今天到这里
        </button>
      </div>
    </div>
  );
}
