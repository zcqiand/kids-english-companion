import { useEffect, useState } from "react";
import { createChild, fetchChildren, fetchCharacters } from "../api";
import type { Character, Child } from "../types";

/** 首启建档 + 选角色；老孩子列表直进（M00.F01.I03）。 */
export default function KidSelect({ onReady }: { onReady: (c: Child) => void }) {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [children, setChildren] = useState<Child[]>([]);
  const [picked, setPicked] = useState<string>("maisy");
  const [name, setName] = useState("");
  const [age, setAge] = useState(5);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchCharacters().then((d) => setCharacters(d.characters)).catch(() => setError("连不上小助手，请确认后端已启动"));
    fetchChildren().then((d) => setChildren(d.children)).catch(() => {});
  }, []);

  async function handleCreate() {
    if (!name.trim()) {
      setError("先告诉我孩子的名字或小名吧");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const { child } = await createChild(name.trim(), age, picked);
      onReady(child);
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建失败，再试一次");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <h1 className="page-title">谁来学英语呀？</h1>
      <p className="page-sub">选一个伙伴，一起玩英语。</p>

      {children.length > 0 && (
        <section className="crayon-card">
          <h2 className="section" style={{ marginTop: 0 }}>继续上次</h2>
          {children.map((c) => {
            const ch = characters.find((x) => x.id === c.character_id);
            return (
              <button key={c.id} className="kid-row" onClick={() => onReady(c)}>
                <span className="face" aria-hidden>{ch?.emoji ?? "🙂"}</span>
                <span>
                  <span className="name">{c.name}</span>
                  <br />
                  <span className="meta">{ch?.name_cn ?? ""} · {c.age} 岁</span>
                </span>
              </button>
            );
          })}
        </section>
      )}

      <section className="crayon-card">
        <h2 className="section" style={{ marginTop: 0 }}>选伙伴</h2>
        <div className="char-grid">
          {characters.map((ch) => (
            <button
              key={ch.id}
              className={`char-card c-${ch.id} ${picked === ch.id ? "selected" : ""}`}
              onClick={() => setPicked(ch.id)}
            >
              <span className="face" aria-hidden>{ch.emoji}</span>
              <span className="name">{ch.name_cn}</span>
              <span className="en">{ch.name_en}</span>
            </button>
          ))}
        </div>

        <h2 className="section">孩子的小档案</h2>
        <div className="field">
          <label htmlFor="kid-name">名字或小名</label>
          <input
            id="kid-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="比如：乐乐"
            maxLength={20}
          />
        </div>
        <div className="field">
          <label htmlFor="kid-age">年龄</label>
          <select id="kid-age" value={age} onChange={(e) => setAge(Number(e.target.value))}>
            {[3, 4, 5, 6, 7, 8, 9].map((a) => (
              <option key={a} value={a}>{a} 岁</option>
            ))}
          </select>
        </div>
        {error && <p className="empty-note" role="alert">{error}</p>}
        <div className="action-row">
          <button className="btn" onClick={handleCreate} disabled={busy}>
            {busy ? "准备中…" : "开始玩英语！"}
          </button>
        </div>
      </section>
    </div>
  );
}
