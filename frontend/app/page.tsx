"use client";
import { useState } from "react";
import NotebookWorkspace from "@/components/NotebookWorkspace";
import { api, Notebook } from "@/lib/api";

export default function Home() {
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [activeNotebook, setActiveNotebook] = useState<Notebook | null>(null);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);

  async function loadNotebooks() {
    if (loaded) return;
    setLoading(true);
    try {
      const list = await api.listNotebooks();
      setNotebooks(list);
    } catch {}
    setLoaded(true);
    setLoading(false);
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const nb = await api.createNotebook(newName.trim());
      setNotebooks((p) => [nb, ...p]);
      setActiveNotebook(nb);
    } finally {
      setCreating(false);
      setNewName("");
    }
  }

  if (activeNotebook) {
    return <NotebookWorkspace notebook={activeNotebook} onBack={() => setActiveNotebook(null)} />;
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "2rem",
        background: "radial-gradient(ellipse 80% 60% at 50% 0%, rgba(108,99,255,0.08) 0%, transparent 60%)",
      }}
    >
      {/* Hero */}
      <div style={{ textAlign: "center", marginBottom: "3rem" }} className="fade-in">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "14px", marginBottom: "1.2rem" }}>
          <div style={{ width: 44, height: 44, borderRadius: "12px", background: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24, boxShadow: "0 0 30px rgba(108,99,255,0.5)" }}>
            ⬡
          </div>
          <h1 style={{ fontSize: "2.4rem", fontWeight: 700 }} className="gradient-text">GraphRAG Notebook</h1>
        </div>
        <p style={{ color: "var(--text-secondary)", fontSize: "1.05rem", maxWidth: 500 }}>
          Hybrid graph + vector retrieval with citation-grounded answers. Upload documents, ask multi-hop questions.
        </p>
      </div>

      {/* Create notebook form */}
      <div className="glass" style={{ padding: "2rem", width: "100%", maxWidth: 480, marginBottom: "2rem" }}>
        <h2 style={{ fontWeight: 600, color: "var(--text-secondary)", marginBottom: "1rem", letterSpacing: "0.5px", textTransform: "uppercase", fontSize: "11px" }}>New Notebook</h2>
        <form onSubmit={handleCreate} style={{ display: "flex", gap: "10px" }}>
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Notebook name..."
            style={{ flex: 1 }}
          />
          <button className="btn btn-primary" type="submit" disabled={creating || !newName.trim()}>
            {creating ? <span className="spinner" /> : "Create"}
          </button>
        </form>
      </div>

      {/* Existing notebooks */}
      <div style={{ width: "100%", maxWidth: 480 }}>
        {!loaded ? (
          <button className="btn btn-ghost" style={{ width: "100%" }} onClick={loadNotebooks} disabled={loading}>
            {loading ? <span className="spinner" /> : "Load existing notebooks"}
          </button>
        ) : notebooks.length === 0 ? (
          <p style={{ textAlign: "center", color: "var(--text-dim)", fontSize: 13 }}>No notebooks yet. Create one above.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {notebooks.map((nb) => (
              <button
                key={nb.notebook_id}
                className="glass btn btn-ghost"
                style={{ width: "100%", justifyContent: "flex-start", padding: "14px 18px" }}
                onClick={() => setActiveNotebook(nb)}
              >
                <span style={{ fontSize: 18 }}>📓</span>
                <div style={{ textAlign: "left" }}>
                  <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{nb.name}</div>
                  <div style={{ fontSize: 12, color: "var(--text-dim)" }}>ID: {nb.notebook_id}</div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
