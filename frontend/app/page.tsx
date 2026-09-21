"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import NotebookWorkspace from "@/components/NotebookWorkspace";
import { api, Notebook } from "@/lib/api";
import { useAuth } from "@/components/AuthContext";
import Login from "@/components/Login";
import { PlusCircle, MessageSquare, Menu, LogOut, X, Trash2, Pin, Pencil, Check, Search } from "lucide-react";

// ── Date grouping (excludes pinned) ─────────────────────────────
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
    if (nb.is_pinned) continue; // pinned go to their own section
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

// ── Delete Confirmation Modal ────────────────────────────────────
function DeleteModal({
  name,
  onConfirm,
  onCancel,
}: {
  name: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onCancel(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onCancel]);

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div style={{ marginBottom: 6 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10,
            background: "rgba(239,68,68,0.15)", border: "1px solid rgba(239,68,68,0.3)",
            display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 14,
          }}>
            <Trash2 size={18} color="#ff6b6b" />
          </div>
          <p style={{ fontWeight: 700, fontSize: 15.5, color: "#e8e8ea", marginBottom: 6 }}>
            Delete chat?
          </p>
          <p style={{ fontSize: 13, color: "#8e8e93", lineHeight: 1.5 }}>
            <span style={{ color: "#c8c8cc", fontWeight: 500 }}>&quot;{name}&quot;</span> will be permanently deleted. This action cannot be undone.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 22, justifyContent: "flex-end" }}>
          <button
            onClick={onCancel}
            style={{
              padding: "8px 16px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.12)",
              background: "rgba(255,255,255,0.06)", color: "#c8c8cc",
              cursor: "pointer", fontSize: 13.5, fontWeight: 500, transition: "background 0.15s",
            }}
            onMouseOver={e => (e.currentTarget.style.background = "rgba(255,255,255,0.1)")}
            onMouseOut={e => (e.currentTarget.style.background = "rgba(255,255,255,0.06)")}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            style={{
              padding: "8px 16px", borderRadius: 8, border: "none",
              background: "linear-gradient(135deg,#ef4444,#dc2626)", color: "#fff",
              cursor: "pointer", fontSize: 13.5, fontWeight: 600,
              boxShadow: "0 2px 10px rgba(239,68,68,0.35)", transition: "opacity 0.15s",
            }}
            onMouseOver={e => (e.currentTarget.style.opacity = "0.88")}
            onMouseOut={e => (e.currentTarget.style.opacity = "1")}
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Single sidebar notebook row ──────────────────────────────────
function NotebookRow({
  nb,
  isActive,
  onSelect,
  onRename,
  onPin,
  onDeleteRequest,
}: {
  nb: Notebook;
  isActive: boolean;
  onSelect: () => void;
  onRename: (id: string, newName: string) => Promise<void>;
  onPin: (id: string, pinned: boolean) => Promise<void>;
  onDeleteRequest: (nb: Notebook) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(nb.name);
  const inputRef = useRef<HTMLInputElement>(null);

  // When edit mode opens, focus the input
  useEffect(() => {
    if (editing) {
      setDraft(nb.name);
      setTimeout(() => inputRef.current?.select(), 30);
    }
  }, [editing, nb.name]);

  const commitRename = async () => {
    setEditing(false);
    const trimmed = draft.trim();
    if (trimmed && trimmed !== nb.name) {
      await onRename(nb.notebook_id, trimmed);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") { e.preventDefault(); commitRename(); }
    if (e.key === "Escape") { setEditing(false); setDraft(nb.name); }
  };

  return (
    <div
      className={`sidebar-item${isActive ? " active" : ""}`}
      onClick={() => { if (!editing) onSelect(); }}
      title={nb.name}
    >
      {/* Chat icon or pin dot */}
      {nb.is_pinned
        ? <span className="pin-dot" />
        : <MessageSquare size={13} style={{ flexShrink: 0, opacity: 0.6 }} />
      }

      {/* Name / rename input */}
      {editing ? (
        <input
          ref={inputRef}
          className="rename-input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={commitRename}
          onClick={(e) => e.stopPropagation()}
        />
      ) : (
        <span style={{
          flex: 1, whiteSpace: "nowrap", overflow: "hidden",
          textOverflow: "ellipsis", fontSize: 13.5,
          paddingRight: 60, // room for action buttons
        }}>
          {nb.name || "Research Chat"}
        </span>
      )}

      {/* Hover action buttons */}
      {!editing && (
        <div className="sidebar-actions" onClick={(e) => e.stopPropagation()}>
          {/* Rename */}
          <button
            className="action-btn"
            title="Rename"
            onClick={() => setEditing(true)}
          >
            <Pencil size={12} />
          </button>
          {/* Pin / Unpin */}
          <button
            className={`action-btn${nb.is_pinned ? " pin-active" : ""}`}
            title={nb.is_pinned ? "Unpin" : "Pin to top"}
            onClick={() => onPin(nb.notebook_id, !nb.is_pinned)}
          >
            <Pin size={12} />
          </button>
          {/* Delete */}
          <button
            className="action-btn danger"
            title="Delete chat"
            onClick={() => onDeleteRequest(nb)}
          >
            <Trash2 size={12} />
          </button>
        </div>
      )}

      {/* Confirm rename button (visible in edit mode) */}
      {editing && (
        <button
          className="action-btn"
          style={{ background: "none", border: "none", cursor: "pointer", color: "#10b981", padding: "2px 4px", display: "flex", alignItems: "center", flexShrink: 0 }}
          onMouseDown={(e) => { e.preventDefault(); commitRename(); }}
          title="Save"
        >
          <Check size={13} />
        </button>
      )}
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────
export default function Home() {
  const { user, loading: authLoading, signOut } = useAuth();
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [activeNotebook, setActiveNotebook] = useState<Notebook | null>(null);
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [search, setSearch] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<Notebook | null>(null);

  const loadNotebooks = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const list = await api.listNotebooks(user.id);
      setNotebooks(list);
      // Also update active notebook so header title refreshes
      setActiveNotebook((prev) => {
        if (!prev) return null;
        const updated = list.find((nb) => nb.notebook_id === prev.notebook_id);
        return updated || null;
      });
    } catch {}
    setLoading(false);
  }, [user]);

  // Reset active state when user changes (login, logout, switch user)
  useEffect(() => {
    setActiveNotebook(null);
    setNotebooks([]);
    if (user) {
      loadNotebooks();
    }
  }, [user?.id, loadNotebooks]);

  async function handleCreateNew() {
    if (!user) return;
    try {
      const name = `New Chat`;
      const res = await api.createNotebook(name, user.id);
      const nb: Notebook = {
        notebook_id: res.notebook_id,
        name,
        description: "",
        created_at: new Date().toISOString(),
        is_pinned: false,
      };
      setNotebooks((p) => [nb, ...p]);
      setActiveNotebook(nb);
    } catch (e) {
      console.error(e);
    }
  }

  async function handleSignOut() {
    setActiveNotebook(null);
    setNotebooks([]);
    await signOut();
  }

  async function handleRename(notebookId: string, newName: string) {
    try {
      await api.renameNotebook(notebookId, newName);
      setNotebooks((prev) =>
        prev.map((nb) => nb.notebook_id === notebookId ? { ...nb, name: newName } : nb)
      );
      if (activeNotebook?.notebook_id === notebookId) {
        setActiveNotebook((nb) => nb ? { ...nb, name: newName } : nb);
      }
    } catch (err) {
      console.error("Rename failed:", err);
    }
  }

  async function handlePin(notebookId: string, pinned: boolean) {
    // Optimistic update
    setNotebooks((prev) =>
      prev.map((nb) => nb.notebook_id === notebookId ? { ...nb, is_pinned: pinned } : nb)
    );
    try {
      await api.pinNotebook(notebookId, pinned);
    } catch (err) {
      console.error("Pin failed:", err);
      loadNotebooks(); // revert on error
    }
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    try {
      await api.deleteNotebook(deleteTarget.notebook_id);
      if (activeNotebook?.notebook_id === deleteTarget.notebook_id) setActiveNotebook(null);
      setNotebooks((prev) => prev.filter((nb) => nb.notebook_id !== deleteTarget.notebook_id));
    } catch (err) {
      console.error("Delete failed:", err);
    } finally {
      setDeleteTarget(null);
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

  // Filter + split notebooks
  const q = search.trim().toLowerCase();
  const filtered = q
    ? notebooks.filter((nb) => nb.name.toLowerCase().includes(q))
    : notebooks;
  const pinned = filtered.filter((nb) => nb.is_pinned);
  const groups = groupNotebooks(filtered);

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: "var(--bg-base)" }}>

      {/* ── Delete modal ──────────────────────────────────────── */}
      {deleteTarget && (
        <DeleteModal
          name={deleteTarget.name}
          onConfirm={confirmDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}

      {/* ── Sidebar ───────────────────────────────────────────── */}
      <aside
        className="sidebar sidebar-scroll"
        style={{ width: sidebarOpen ? 262 : 0, overflowY: sidebarOpen ? "auto" : "hidden" }}
      >
        {/* Branding + New Chat */}
        <div style={{ padding: "18px 16px 10px", borderBottom: "1px solid var(--sidebar-border)", flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
            <div style={{
              width: 32, height: 32, borderRadius: 8, flexShrink: 0,
              background: "linear-gradient(135deg, #6366f1 0%, #a855f7 60%, #ec4899 100%)",
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "0 2px 10px rgba(99,102,241,0.5)",
            }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill="white" opacity="0.95"/>
              </svg>
            </div>
            <span style={{ color: "var(--sidebar-text)", fontWeight: 800, fontSize: 16, whiteSpace: "nowrap", letterSpacing: "-0.3px" }}>
              Lumina
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

        {/* Search bar */}
        <div className="sidebar-search">
          <Search size={13} color="var(--sidebar-text-muted)" style={{ flexShrink: 0 }} />
          <input
            placeholder="Search chats…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              style={{ background: "none", border: "none", cursor: "pointer", color: "var(--sidebar-text-muted)", display: "flex", padding: 0 }}
            >
              <X size={12} />
            </button>
          )}
        </div>

        {/* Chat History */}
        <div style={{ flex: 1, padding: "10px 8px", display: "flex", flexDirection: "column", gap: 0, minWidth: 230 }}>
          {loading ? (
            <div style={{ display: "flex", justifyContent: "center", padding: "24px 0" }}>
              <span className="spinner" style={{ borderTopColor: "#b5704a" }} />
            </div>
          ) : filtered.length === 0 ? (
            <div style={{ textAlign: "center", color: "var(--sidebar-text-muted)", fontSize: 13, padding: "24px 12px" }}>
              {search ? `No chats matching "${search}"` : "No chats yet. Start one!"}
            </div>
          ) : (
            <>
              {/* ── Pinned section ── */}
              {pinned.length > 0 && (
                <div style={{ marginBottom: 6 }}>
                  <div className="sidebar-section-label" style={{ padding: "8px 8px 4px", display: "flex", alignItems: "center", gap: 5 }}>
                    <Pin size={10} />
                    Pinned
                  </div>
                  {pinned.map((nb) => (
                    <NotebookRow
                      key={nb.notebook_id}
                      nb={nb}
                      isActive={activeNotebook?.notebook_id === nb.notebook_id}
                      onSelect={() => setActiveNotebook(nb)}
                      onRename={handleRename}
                      onPin={handlePin}
                      onDeleteRequest={setDeleteTarget}
                    />
                  ))}
                </div>
              )}

              {/* ── Date groups ── */}
              {groups.map((group) => (
                <div key={group.label} style={{ marginBottom: 6 }}>
                  <div className="sidebar-section-label" style={{ padding: "8px 8px 4px" }}>
                    {group.label}
                  </div>
                  {group.items.map((nb) => (
                    <NotebookRow
                      key={nb.notebook_id}
                      nb={nb}
                      isActive={activeNotebook?.notebook_id === nb.notebook_id}
                      onSelect={() => setActiveNotebook(nb)}
                      onRename={handleRename}
                      onPin={handlePin}
                      onDeleteRequest={setDeleteTarget}
                    />
                  ))}
                </div>
              ))}
            </>
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
              onClick={handleSignOut}
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
              width: 56, height: 56, borderRadius: 16,
              background: "linear-gradient(135deg, #6366f1 0%, #a855f7 60%, #ec4899 100%)",
              display: "flex", alignItems: "center", justifyContent: "center",
              marginBottom: 24,
              boxShadow: "0 8px 32px rgba(99,102,241,0.35)"
            }}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill="white" opacity="0.95"/>
              </svg>
            </div>
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
