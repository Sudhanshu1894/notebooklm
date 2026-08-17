"use client";
import { useState, useEffect } from "react";
import NotebookWorkspace from "@/components/NotebookWorkspace";
import { api, Notebook } from "@/lib/api";
import { useAuth } from "@/components/AuthContext";
import Login from "@/components/Login";
import { PlusCircle, MessageSquare, Menu, LogOut, X, Trash2 } from "lucide-react";

function groupNotebooks(notebooks: Notebook[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
  const week = new Date(today); week.setDate(today.getDate() - 7);
  const month = new Date(today); month.setDate(today.getDate() - 30);

  const groups: { label: string; items: Notebook[] }[] = [
    { label: "Today", items: [] },
    { label: "Yesterday", items: [] },
    { label: "Past 7 Days", items: [] },
    { label: "Past 30 Days", items: [] },
    { label: "Older", items: [] },
  ];

  for (const nb of notebooks) {
    const d = new Date(nb.created_at || Date.now());
    const day = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    if (day >= today) groups[0].items.push(nb);
    else if (day >= yesterday) groups[1].items.push(nb);
    else if (day >= week) groups[2].items.push(nb);
    else if (day >= month) groups[3].items.push(nb);
    else groups[4].items.push(nb);
  }

  return groups.filter((g) => g.items.length > 0);
}

export default function Home() {
  const { user, loading: authLoading, signOut } = useAuth();
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [activeNotebook, setActiveNotebook] = useState<Notebook | null>(null);
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  async function loadNotebooks() {
    setLoading(true);
    try {
      const list = await api.listNotebooks();
      setNotebooks(list);
    } catch {}
    setLoading(false);
  }

  useEffect(() => {
    if (user) loadNotebooks();
  }, [user]);

  async function handleCreateNew() {
    try {
      const name = `New Chat`;
      const res = await api.createNotebook(name);
      const nb: Notebook = {
        notebook_id: res.notebook_id,
        name,
        description: "",
        created_at: new Date().toISOString(),
      };
      setNotebooks((p) => [nb, ...p]);
      setActiveNotebook(nb);
    } catch (e) {
      console.error(e);
    }
  }

  async function handleDeleteNotebook(notebookId: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm("Delete this chat?")) return;
    try {
      await api.deleteNotebook(notebookId);
      if (activeNotebook?.notebook_id === notebookId) setActiveNotebook(null);
      loadNotebooks();
    } catch (err) {
      console.error("Failed to delete notebook", err);
    }
  }

  if (authLoading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#1c1c1e" }}>
        <span className="spinner" style={{ width: 28, height: 28, borderWidth: 3, borderTopColor: "#b5704a" }} />
      </div>
    );
  }
  if (!user) return <Login />;

  const groups = groupNotebooks(notebooks);

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: "var(--bg-base)" }}>
      {/* ── Sidebar ───────────────────────────────────────────── */}
      <aside
        className="sidebar sidebar-scroll"
        style={{ width: sidebarOpen ? 260 : 0, overflowY: sidebarOpen ? "auto" : "hidden" }}
      >
        {/* Branding */}
        <div style={{ padding: "18px 16px 12px", borderBottom: "1px solid var(--sidebar-border)", flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
            <div style={{
              width: 32, height: 32, borderRadius: 8,
              background: "linear-gradient(135deg, #b5704a, #c97d50)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 16, flexShrink: 0
            }}>⬡</div>
            <span style={{ color: "var(--sidebar-text)", fontWeight: 700, fontSize: 15, whiteSpace: "nowrap" }}>
              Research AI
            </span>
          </div>
          <button
            onClick={handleCreateNew}
            style={{
              width: "100%", display: "flex", alignItems: "center", gap: 8,
              padding: "9px 12px", borderRadius: 8, border: "1px solid var(--sidebar-border)",
              background: "rgba(255,255,255,0.06)", color: "var(--sidebar-text)",
              cursor: "pointer", fontSize: 13.5, fontWeight: 500,
              transition: "background 0.15s", whiteSpace: "nowrap"
            }}
            onMouseOver={e => (e.currentTarget.style.background = "rgba(255,255,255,0.1)")}
            onMouseOut={e => (e.currentTarget.style.background = "rgba(255,255,255,0.06)")}
          >
            <PlusCircle size={15} />
            New Chat
          </button>
        </div>

        {/* Chat History */}
        <div style={{ flex: 1, padding: "12px 10px", display: "flex", flexDirection: "column", gap: 0, minWidth: 230 }}>
          {loading ? (
            <div style={{ display: "flex", justifyContent: "center", padding: "24px 0" }}>
              <span className="spinner" style={{ borderTopColor: "#b5704a" }} />
            </div>
          ) : notebooks.length === 0 ? (
            <div style={{ textAlign: "center", color: "var(--sidebar-text-muted)", fontSize: 13, padding: "24px 12px" }}>
              No chats yet. Start one!
            </div>
          ) : (
            groups.map((group) => (
              <div key={group.label} style={{ marginBottom: 8 }}>
                <div className="sidebar-section-label" style={{ padding: "8px 8px 4px" }}>
                  {group.label}
                </div>
                {group.items.map((nb) => (
                  <div
                    key={nb.notebook_id}
                    className={`sidebar-item${activeNotebook?.notebook_id === nb.notebook_id ? " active" : ""}`}
                    onClick={() => setActiveNotebook(nb)}
                    title={nb.name}
                  >
                    <MessageSquare size={14} style={{ flexShrink: 0, opacity: 0.7 }} />
                    <span style={{
                      flex: 1, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                      fontSize: 13.5, paddingRight: 20
                    }}>
                      {nb.name || "Research Chat"}
                    </span>
                    <button
                      className="delete-btn"
                      onClick={(e) => handleDeleteNotebook(nb.notebook_id, e)}
                      title="Delete chat"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}
              </div>
            ))
          )}
        </div>

        {/* User section */}
        <div style={{
          padding: "12px 14px",
          borderTop: "1px solid var(--sidebar-border)",
          flexShrink: 0, minWidth: 230
        }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 10,
            padding: "8px 10px", borderRadius: 8,
          }}>
            <div style={{
              width: 30, height: 30, borderRadius: "50%",
              background: "linear-gradient(135deg, #b5704a, #c97d50)",
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "#fff", fontSize: 13, fontWeight: 700, flexShrink: 0
            }}>
              {user.email?.[0]?.toUpperCase() ?? "U"}
            </div>
            <span style={{
              flex: 1, fontSize: 12.5, color: "var(--sidebar-text-dim)",
              whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis"
            }}>
              {user.email}
            </span>
            <button
              onClick={signOut}
              title="Log out"
              style={{
                background: "none", border: "none", cursor: "pointer",
                color: "var(--sidebar-text-muted)", padding: 4, borderRadius: 6,
                display: "flex", alignItems: "center", transition: "color 0.15s"
              }}
              onMouseOver={e => (e.currentTarget.style.color = "#ff6b6b")}
              onMouseOut={e => (e.currentTarget.style.color = "var(--sidebar-text-muted)")}
            >
              <LogOut size={15} />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main Content ──────────────────────────────────────── */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", position: "relative", minWidth: 0 }}>
        {/* Sidebar toggle */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          style={{
            position: "absolute", top: 16, left: 16, zIndex: 50,
            background: "var(--bg-panel)", border: "1px solid var(--border)",
            borderRadius: 8, padding: 7, cursor: "pointer",
            color: "var(--text-secondary)", boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
            display: "flex", alignItems: "center", transition: "background 0.15s"
          }}
        >
          {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
        </button>

        {activeNotebook ? (
          <NotebookWorkspace
            notebook={activeNotebook}
            onBack={() => setActiveNotebook(null)}
            onTitleChange={loadNotebooks}
          />
        ) : (
          /* Welcome / empty state */
          <div style={{
            flex: 1, display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center", padding: "2rem"
          }}>
            <div style={{
              width: 60, height: 60, borderRadius: 16,
              background: "linear-gradient(135deg, #b5704a, #c97d50)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 28, marginBottom: 24,
              boxShadow: "0 8px 32px rgba(181,112,74,0.3)"
            }}>⬡</div>
            <h1
              style={{ fontSize: "1.85rem", fontWeight: 700, marginBottom: "0.75rem" }}
              className="gradient-text"
            >
              How can I help you today?
            </h1>
            <p style={{
              color: "var(--text-secondary)", fontSize: "1rem",
              maxWidth: 400, textAlign: "center", lineHeight: 1.6, marginBottom: "2rem"
            }}>
              Start a new research chat or pick up where you left off.
            </p>
            <button
              className="btn btn-primary"
              style={{ padding: "11px 24px", fontSize: 15 }}
              onClick={handleCreateNew}
            >
              <PlusCircle size={18} /> New Chat
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
