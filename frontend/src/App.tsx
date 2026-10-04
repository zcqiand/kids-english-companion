import { useCallback, useEffect, useState } from "react";
import KidSelect from "./pages/KidSelect";
import Chat from "./pages/Chat";
import Readalong from "./pages/Readalong";
import Pronunciation from "./pages/Pronunciation";
import ParentBoard from "./pages/ParentBoard";
import { fetchChildren } from "./api";
import type { Child } from "./types";

const CHILD_KEY = "kids-english.child_id";

export type PageId = "chat" | "readalong" | "pronunciation" | "parent";

/** 应用壳：孩子状态 + 页面切换。未选孩子 → KidSelect。 */
export default function App() {
  const [child, setChild] = useState<Child | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState<PageId>("chat");

  useEffect(() => {
    const saved = localStorage.getItem(CHILD_KEY);
    if (!saved) {
      setLoading(false);
      return;
    }
    fetchChildren()
      .then(({ children }) => {
        const hit = children.find((c) => c.id === saved);
        if (hit) setChild(hit);
        else localStorage.removeItem(CHILD_KEY);
      })
      .catch(() => {
        // 后端未起：留在选择页并给出提示
      })
      .finally(() => setLoading(false));
  }, []);

  const handleReady = useCallback((c: Child) => {
    localStorage.setItem(CHILD_KEY, c.id);
    setChild(c);
    setPage("chat");
  }, []);

  const handleSwitch = useCallback(() => {
    localStorage.removeItem(CHILD_KEY);
    setChild(null);
  }, []);

  if (loading) {
    return <div className="page empty-note">加载中…</div>;
  }
  if (!child) {
    return <KidSelect onReady={handleReady} />;
  }
  return (
    <>
      <header className="topbar">
        <span className="brand">
          英语<span className="accent">启蒙伙伴</span>
        </span>
        <span className="spacer" />
        <span className="streak-badge">🔥 {child.name} · {child.age} 岁</span>
        <button className="say-btn" onClick={handleSwitch}>
          换孩子
        </button>
        <span className="streak-badge" style={{ display: "none" }} data-streak-hook />
      </header>
      <main className="page">
        {page === "chat" && <Chat child={child} />}
        {page === "readalong" && <Readalong child={child} />}
        {page === "pronunciation" && <Pronunciation child={child} />}
        {page === "parent" && <ParentBoard child={child} />}
      </main>
      <nav className="tabbar">
        <TabButton id="chat" page={page} setPage={setPage} icon="💬" label="聊天" />
        <TabButton id="readalong" page={page} setPage={setPage} icon="📖" label="跟读" />
        <TabButton id="pronunciation" page={page} setPage={setPage} icon="🎤" label="发音" />
        <TabButton id="parent" page={page} setPage={setPage} icon="👨‍👩‍👧" label="看板" />
      </nav>
    </>
  );
}

function TabButton({
  id,
  page,
  setPage,
  icon,
  label,
}: {
  id: PageId;
  page: PageId;
  setPage: (p: PageId) => void;
  icon: string;
  label: string;
}) {
  return (
    <button
      className={`tab ${page === id ? "active" : ""}`}
      onClick={() => setPage(id)}
      aria-current={page === id}
    >
      <span className="icon" aria-hidden>
        {icon}
      </span>
      {label}
    </button>
  );
}
