"use client";
import { useState, useEffect } from "react";
import { api, KnowledgeItem, KnowledgeStats } from "@/lib/api";
import { Database, Tag, Lightbulb, FileText, Bot, ChevronDown, ChevronRight, RefreshCw } from "lucide-react";

const TYPE_CONFIG: Record<string, { icon: React.ReactNode; label: string; color: string; bg: string }> = {
  summary:  { icon: <FileText size={14} />, label: "Summaries",  color: "#b5704a", bg: "rgba(181,112,74,0.10)" },
  entity:   { icon: <Tag size={14} />,      label: "Entities",   color: "#6366f1", bg: "rgba(99,102,241,0.10)" },
  concept:  { icon: <Lightbulb size={14} />, label: "Concepts", color: "#10b981", bg: "rgba(16,185,129,0.10)" },
  fact:     { icon: <Database size={14} />,  label: "Facts",     color: "#f59e0b", bg: "rgba(245,158,11,0.10)" },
};

export default function KnowledgeExplorer({ notebookId }: { notebookId: string }) {
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [systemPrompt, setSystemPrompt] = useState("");
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  const [promptOpen, setPromptOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const [s, k, p] = await Promise.all([
        api.getKnowledgeStats(notebookId),
        api.getKnowledge(notebookId, activeFilter || undefined),
        api.getSystemPrompt(notebookId),
      ]);
      setStats(s);
      setItems(k.items);
      setSystemPrompt(p.system_prompt);
    } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => { loadData(); }, [notebookId, activeFilter]);

  if (loading && !stats) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-dim)" }}>
        <span className="spinner" /> Loading knowledge...
      </div>
    );
  }

  const isEmpty = !stats || stats.total_items === 0;

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "28px 24px", display: "flex", flexDirection: "column", alignItems: "center" }}>
      <div style={{ width: "100%", maxWidth: 780 }}>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10,
            background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 4px 16px rgba(99,102,241,0.3)"
          }}>
            <Database size={20} color="#fff" />
          </div>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
              Knowledge Explorer
            </h2>
            <p style={{ fontSize: 12, color: "var(--text-dim)", margin: 0, marginTop: 2 }}>
              What the AI has learned from your documents
            </p>
          </div>
          <button
            onClick={loadData}
            style={{
              marginLeft: "auto", display: "flex", alignItems: "center", gap: 6,
              padding: "6px 12px", borderRadius: 8, border: "1px solid var(--border)",
              background: "var(--bg-panel)", cursor: "pointer", fontSize: 12, fontWeight: 600,
              color: "var(--text-secondary)", transition: "all 0.18s"
            }}
          >
            <RefreshCw size={12} /> Refresh
          </button>
        </div>

        {/* Empty State */}
        {isEmpty && (
          <div className="fade-in" style={{
            textAlign: "center", padding: "60px 20px", color: "var(--text-dim)",
            background: "var(--bg-panel)", borderRadius: 16, border: "1px solid var(--border)"
          }}>
            <Database size={40} strokeWidth={1.2} style={{ opacity: 0.3, marginBottom: 16 }} />
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>No knowledge extracted yet</div>
            <div style={{ fontSize: 13, lineHeight: 1.6 }}>
              Upload a PDF, DOCX, PPTX, or TXT document to train the AI.<br />
              Knowledge will be extracted automatically.
            </div>
          </div>
        )}

        {!isEmpty && stats && (
          <>
            {/* Stats Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 20 }}>
              {Object.entries(TYPE_CONFIG).map(([type, cfg]) => {
                const count = stats.by_type[type] || 0;
                const isActive = activeFilter === type;
                return (
                  <button
                    key={type}
                    onClick={() => setActiveFilter(isActive ? null : type)}
                    style={{
                      display: "flex", flexDirection: "column", alignItems: "center", gap: 6,
                      padding: "14px 8px", borderRadius: 12,
                      border: isActive ? `2px solid ${cfg.color}` : "1px solid var(--border)",
                      background: isActive ? cfg.bg : "var(--bg-panel)",
                      cursor: "pointer", transition: "all 0.18s",
                      boxShadow: isActive ? `0 2px 12px ${cfg.color}30` : "none",
                    }}
                  >
                    <div style={{ color: cfg.color, display: "flex", alignItems: "center", gap: 5, fontSize: 12, fontWeight: 600 }}>
                      {cfg.icon} {cfg.label}
                    </div>
                    <div style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)" }}>{count}</div>
                  </button>
                );
              })}
            </div>

            {/* Ollama Status */}
            <div style={{
              display: "flex", alignItems: "center", gap: 10, padding: "10px 14px",
              borderRadius: 10, background: "var(--bg-panel)", border: "1px solid var(--border)",
              marginBottom: 20
            }}>
              <Bot size={16} color={stats.ollama_available ? "#10b981" : "var(--text-dim)"} />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>
                  Ollama Model Status
                </div>
                <div style={{ fontSize: 11, color: "var(--text-dim)", marginTop: 2 }}>
                  {stats.ollama_available
                    ? `✓ Trained model active: ${stats.ollama_model}`
                    : `○ Not registered (Ollama may not be running)`
                  }
                </div>
              </div>
              <span style={{
                fontSize: 11, fontWeight: 600, padding: "3px 10px", borderRadius: 20,
                background: stats.ollama_available ? "rgba(16,185,129,0.15)" : "rgba(0,0,0,0.05)",
                color: stats.ollama_available ? "#10b981" : "var(--text-dim)",
              }}>
                {stats.ollama_available ? "Active" : "Inactive"}
              </span>
            </div>

            {/* Knowledge Items */}
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 20 }}>
              {items.map((item) => {
                const cfg = TYPE_CONFIG[item.knowledge_type] || TYPE_CONFIG.fact;
                const meta = item.metadata || {};
                return (
                  <div key={item.id} className="fade-in" style={{
                    padding: "12px 16px", borderRadius: 12,
                    background: "var(--bg-panel)", border: "1px solid var(--border)",
                    transition: "all 0.18s",
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                      <span style={{
                        display: "inline-flex", alignItems: "center", gap: 4,
                        padding: "2px 8px", borderRadius: 6, fontSize: 11, fontWeight: 600,
                        background: cfg.bg, color: cfg.color,
                      }}>
                        {cfg.icon} {cfg.label.slice(0, -1)}
                      </span>
                      {String((meta as Record<string, string>).entity_type || "") && (meta as Record<string, string>).entity_type && (
                        <span style={{ fontSize: 10, color: "var(--text-dim)", fontWeight: 600, textTransform: "uppercase" }}>
                          {String((meta as Record<string, string>).entity_type)}
                        </span>
                      )}
                      {Number((meta as Record<string, number>).frequency || 0) > 0 && (
                        <span style={{ fontSize: 10, color: "var(--text-dim)" }}>
                          &times;{String((meta as Record<string, number>).frequency)}
                        </span>
                      )}
                      <span style={{ fontSize: 10, color: "var(--text-dim)", marginLeft: "auto" }}>
                        {String((meta as Record<string, string>).doc_id || item.doc_id)}
                      </span>
                    </div>
                    <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.6 }}>
                      {item.content}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* System Prompt Transparency */}
            <div style={{
              borderRadius: 12, background: "var(--bg-panel)",
              border: "1px solid var(--border)", overflow: "hidden",
            }}>
              <button
                onClick={() => setPromptOpen(!promptOpen)}
                style={{
                  width: "100%", display: "flex", alignItems: "center", gap: 8,
                  padding: "12px 16px", background: "transparent", border: "none",
                  cursor: "pointer", fontSize: 13, fontWeight: 600, color: "var(--text-secondary)",
                }}
              >
                <Bot size={14} />
                AI System Prompt (Transparency)
                <span style={{ marginLeft: "auto" }}>
                  {promptOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </span>
              </button>
              {promptOpen && (
                <div style={{
                  padding: "0 16px 16px", borderTop: "1px solid var(--border)",
                }}>
                  <pre style={{
                    fontSize: 11, color: "var(--text-dim)", lineHeight: 1.7,
                    whiteSpace: "pre-wrap", wordBreak: "break-word",
                    background: "rgba(0,0,0,0.03)", padding: 14, borderRadius: 8,
                    marginTop: 12, maxHeight: 400, overflowY: "auto",
                    fontFamily: "monospace",
                  }}>
                    {systemPrompt || "No system prompt generated yet."}
                  </pre>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
