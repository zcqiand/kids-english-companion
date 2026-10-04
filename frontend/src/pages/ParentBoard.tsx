import { useEffect, useState } from "react";
import { fetchDashboard } from "../api";
import type { Child } from "../types";
import type { Dashboard } from "../api";

const KIND_LABEL: Record<string, string> = {
  encounter: "对话带出",
  free_use: "主动开口",
  echo_attempt: "跟读",
  pronunciation_attempt: "发音练习",
};

function statusClass(status: string): string {
  if (status === "已掌握") return "st-mastered";
  if (status === "巩固中") return "st-growing";
  return "st-learning";
}

/** 家长看板（M05.F01.I01）：掌握度全景 + 今日复习 + 薄弱 + 连击 + 14 天活动。 */
export default function ParentBoard({ child }: { child: Child }) {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchDashboard(child.id)
      .then((d) => setData(d.dashboard))
      .catch((e) => setError(e instanceof Error ? e.message : "取看板失败"));
  }, [child.id]);

  if (error) return <div className="empty-note" role="alert">{error}</div>;
  if (!data) return <div className="empty-note">看板准备中…</div>;

  const days = Object.entries(data.activity);
  const maxDay = Math.max(1, ...days.map(([, n]) => n));

  return (
    <div>
      <h1 className="page-title">{child.name} 的英语小看板</h1>
      <p className="page-sub">学过的词、今天该复习的词、哪里还薄弱，都在这里。</p>

      <div className="stats-row">
        <div className="stat-box streak">
          <div className="num">🔥{data.streak}</div>
          <div className="lbl">连续天数</div>
        </div>
        <div className="stat-box due">
          <div className="num">{data.due_today.length}</div>
          <div className="lbl">今日复习</div>
        </div>
        <div className="stat-box weak-c">
          <div className="num">{data.weak.length}</div>
          <div className="lbl">薄弱词</div>
        </div>
        <div className="stat-box mastered">
          <div className="num">{data.stats["已掌握"]}</div>
          <div className="lbl">已掌握</div>
        </div>
      </div>

      <section className="crayon-card">
        <h2 className="section" style={{ marginTop: 0 }}>最近 14 天</h2>
        <div className="activity-strip" role="img" aria-label="近 14 天学习活动">
          {days.map(([day, n]) => (
            <div
              key={day}
              className={`day ${n > 0 ? "has-session" : ""}`}
              style={{ height: `${8 + (n / maxDay) * 40}px` }}
              title={`${day}：${n} 次学习`}
            />
          ))}
        </div>
        <div className="activity-legend">
          {days.length ? `${days[0][0].slice(5)} — 今天，每天一次会话记一格` : "还没有学习记录"}
        </div>
      </section>

      <section className="crayon-card">
        <h2 className="section" style={{ marginTop: 0 }}>
          词汇掌握全景 <span style={{ fontWeight: 400, color: "var(--ink-soft)", fontSize: 13 }}>
            （共 {data.stats.total_known} 词）
          </span>
        </h2>
        {data.words.length === 0 ? (
          <div className="empty-note">还没开始学词，先去和伙伴聊聊天吧。</div>
        ) : (
          <div className="word-cell-grid">
            {data.words.map((w) => (
              <span
                key={String(w.word_id ?? w.text)}
                className={`word-cell ${statusClass(w.status)} ${w.weak ? "is-weak" : ""}`}
                title={`${w.text} · ${w.status}${w.weak ? " · 薄弱" : ""}`}
              >
                {w.text}
              </span>
            ))}
          </div>
        )}
      </section>

      <div style={{ display: "grid", gap: 16 }}>
        <section className="crayon-card" style={{ marginBottom: 0 }}>
          <h2 className="section" style={{ marginTop: 0 }}>今日该复习</h2>
          {data.due_today.length === 0 ? (
            <div className="empty-note">今天没有到期的词，轻松一天。</div>
          ) : (
            <div className="word-cell-grid">
              {data.due_today.map((t) => (
                <span key={t} className="word-cell st-learning">{t}</span>
              ))}
            </div>
          )}
          {data.weak.length > 0 && (
            <>
              <h2 className="section">薄弱词（多鼓励，别纠正过头）</h2>
              <div className="word-cell-grid">
                {data.weak.map((t) => (
                  <span key={t} className="word-cell is-weak">{t}</span>
                ))}
              </div>
            </>
          )}
        </section>

        <section className="crayon-card" style={{ marginBottom: 0 }}>
          <h2 className="section" style={{ marginTop: 0 }}>最近在学</h2>
          {data.recent_events.length === 0 ? (
            <div className="empty-note">还没有记录。</div>
          ) : (
            <ul className="event-list">
              {data.recent_events.map((e) => (
                <li key={e.id}>
                  <span className="when">{formatWhen(e.happened_at)}</span>
                  <span>
                    <span className="kind">{KIND_LABEL[e.kind] ?? e.kind}</span>{" "}
                    <b>{e.word}</b> — {e.success ? "说对了" : "还需练习"}
                    {e.detail ? `（${e.detail}）` : ""}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}

function formatWhen(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:${String(
    d.getMinutes(),
  ).padStart(2, "0")}`;
}
