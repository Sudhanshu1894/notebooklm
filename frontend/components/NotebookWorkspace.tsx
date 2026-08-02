"use client";
import { useState, useEffect, useRef } from "react";
import { Notebook, Document, ChatResponse, Citation, api } from "@/lib/api";
import GraphExplorer from "./GraphExplorer";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  route?: string;
  is_insufficient?: boolean;
}

export default function NotebookWorkspace({ notebook, onBack }: { notebook: Notebook; onBack: () => void }) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [query, setQuery] = useState("");
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [activeTab, setActiveTab] = useState<"chat" | "graph">("chat");
  const fileRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const pollingRef = useRef<Record<string, NodeJS.Timeout>>({});

  useEffect(() => {
    api.listSources(notebook.notebook_id).then(setDocuments).catch(() => {});
    return () => Object.values(pollingRef.current).forEach(clearInterval);
  }, [notebook.notebook_id]);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  function pollDocument(docId: string) {
    const timer = setInterval(async () => {
      try {
        const doc = await api.getDocumentStatus(notebook.notebook_id, docId);
        setDocuments((prev) => prev.map((d) => (d.doc_id === docId ? doc : d)));
        if (doc.status === "ready" || doc.status === "failed") {
          clearInterval(timer);
          delete pollingRef.current[docId];
        }
      } catch { clearInterval(timer); }
    }, 2000);
    pollingRef.current[docId] = timer;
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const res = await api.uploadDocument(notebook.notebook_id, file);
      const tempDoc: Document = { doc_id: res.doc_id, filename: file.name, status: "processing", chunk_count: 0, error_message: "", created_at: new Date().toISOString(), updated_at: new Date().toISOString() };
      setDocuments((p) => [tempDoc, ...p]);
      pollDocument(res.doc_id);
    } catch (err) { alert("Upload failed: " + err); }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = ""; }
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim() || sending) return;
    const q = query.trim();
    setQuery("");
    const userMsg: Message = { id: Date.now().toString(), role: "user", content: q };
    setMessages((p) => [...p, userMsg]);
    setSending(true);
    try {
      const result: ChatResponse = await api.chat(notebook.notebook_id, q);
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: result.answer,
        citations: result.citations,
        route: result.route,
        is_insufficient: result.is_insufficient,
      };
      setMessages((p) => [...p, assistantMsg]);
    } catch (err) {
      setMessages((p) => [...p, { id: Date.now().toString(), role: "assistant", content: `Error: ${err}` }]);
    } finally { setSending(false); }
  }

  function renderAnswer(text: string, citations: Citation[]) {
    const parts = text.split(/(\[\d+\])/g);
    return parts.map((part, i) => {
      const match = part.match(/^\[(\d+)\]$/);
      if (match) {
        const num = parseInt(match[1]);
        const cit = citations.find((c) => c.citation_number === num);
        return (
          <span
            key={i}
            className={`citation-pill ${activeCitation?.citation_number === num ? "active" : ""}`}
            onClick={() => setActiveCitation(cit === activeCitation ? null : cit || null)}
            title={cit?.text_preview || ""}
          >
            {num}
          </span>
        );
      }
      return <span key={i}>{part}</span>;
    });
  }

  const statusBadge = (status: string) => {
    if (status === "ready") return <span className="badge badge-ready">● Ready</span>;
    if (status === "failed") return <span className="badge badge-failed">✗ Failed</span>;
    return <span className="badge badge-pending"><span className="spinner" style={{ width: 8, height: 8, borderWidth: 1.5 }} /> Processing</span>;
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      {/* Top bar */}
      <header className="glass" style={{ borderRadius: 0, borderLeft: "none", borderRight: "none", borderTop: "none", padding: "12px 20px", display: "flex", alignItems: "center", gap: "14px", flexShrink: 0 }}>
        <button className="btn btn-ghost" style={{ padding: "7px 12px", fontSize: 13 }} onClick={onBack}>← Back</button>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 20 }}>📓</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: "1rem" }}>{notebook.name}</div>
            <div style={{ fontSize: 11, color: "var(--text-dim)" }}>ID: {notebook.notebook_id}</div>
          </div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          {(["chat", "graph"] as const).map((tab) => (
            <button key={tab} className={`btn ${activeTab === tab ? "btn-primary" : "btn-ghost"}`} style={{ padding: "7px 16px", fontSize: 13 }} onClick={() => setActiveTab(tab)}>
              {tab === "chat" ? "💬 Chat" : "⬡ Graph"}
            </button>
          ))}
        </div>
      </header>

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Left: Sources panel */}
        <aside style={{ width: 260, flexShrink: 0, borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column", padding: "16px", gap: "12px", overflowY: "auto" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.5px" }}>Sources</span>
            <button className="btn btn-primary" style={{ padding: "6px 12px", fontSize: 12 }} onClick={() => fileRef.current?.click()} disabled={uploading}>
              {uploading ? <span className="spinner" /> : "+ Upload"}
            </button>
            <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" style={{ display: "none" }} onChange={handleUpload} />
          </div>

          {documents.length === 0 ? (
            <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8, color: "var(--text-dim)", textAlign: "center" }}>
              <span style={{ fontSize: 32 }}>📂</span>
              <span style={{ fontSize: 12 }}>Upload PDF, DOCX or TXT to get started</span>
            </div>
          ) : (
            documents.map((doc) => (
              <div key={doc.doc_id} className="glass" style={{ padding: "12px" }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, wordBreak: "break-word" }}>{doc.filename}</div>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  {statusBadge(doc.status)}
                  {doc.chunk_count > 0 && <span style={{ fontSize: 10, color: "var(--text-dim)" }}>{doc.chunk_count} chunks</span>}
                </div>
                {doc.error_message && <div style={{ fontSize: 10, color: "var(--error)", marginTop: 4 }}>{doc.error_message}</div>}
              </div>
            ))
          )}
        </aside>

        {/* Main: Chat or Graph */}
        <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {activeTab === "graph" ? (
            <GraphExplorer notebookId={notebook.notebook_id} />
          ) : (
            <>
              {/* Chat messages */}
              <div style={{ flex: 1, overflowY: "auto", padding: "20px", display: "flex", flexDirection: "column", gap: "16px" }}>
                {messages.length === 0 && (
                  <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, color: "var(--text-dim)" }}>
                    <span style={{ fontSize: 48 }}>💬</span>
                    <span style={{ fontSize: 14 }}>Ask a question about your documents</span>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", maxWidth: 500 }}>
                      {["What is the main topic?", "Compare the two authors' approaches", "Which events led to the outcome?"].map((q) => (
                        <button key={q} className="btn btn-ghost" style={{ fontSize: 12, padding: "7px 14px" }} onClick={() => setQuery(q)}>{q}</button>
                      ))}
                    </div>
                  </div>
                )}

                {messages.map((msg) => (
                  <div key={msg.id} className="fade-in" style={{ display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }}>
                    {msg.role === "user" ? (
                      <div style={{ background: "var(--accent)", color: "white", padding: "10px 16px", borderRadius: "16px 16px 4px 16px", maxWidth: "65%", fontSize: 14 }}>
                        {msg.content}
                      </div>
                    ) : (
                      <div style={{ maxWidth: "80%", display: "flex", flexDirection: "column", gap: 8 }}>
                        <div className="glass" style={{ padding: "16px", lineHeight: 1.7, fontSize: 14 }}>
                          {msg.citations && msg.citations.length > 0 ? (
                            <span style={{ display: "inline" }}>{renderAnswer(msg.content, msg.citations)}</span>
                          ) : msg.content}
                        </div>

                        {/* Route badge */}
                        {msg.route && (
                          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                            <span className={`badge ${msg.route === "hybrid" ? "badge-graph" : "badge-vector"}`}>
                              {msg.route === "hybrid" ? "⬡ Graph+Vector" : "⬥ Vector only"}
                            </span>
                            {msg.is_insufficient && <span className="badge badge-failed">⚠ Insufficient context</span>}
                          </div>
                        )}

                        {/* Citations panel */}
                        {msg.citations && msg.citations.length > 0 && (
                          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                            <div style={{ fontSize: 11, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.5px" }}>Sources</div>
                            {msg.citations.map((c) => (
                              <div
                                key={c.citation_number}
                                className={`glass ${activeCitation?.citation_number === c.citation_number ? "glass-accent" : ""}`}
                                style={{ padding: "10px 14px", cursor: "pointer", transition: "all 0.2s", display: "flex", gap: 10, alignItems: "flex-start" }}
                                onClick={() => setActiveCitation(activeCitation?.citation_number === c.citation_number ? null : c)}
                              >
                                <span className="citation-pill" style={{ cursor: "default" }}>{c.citation_number}</span>
                                <div style={{ flex: 1, minWidth: 0 }}>
                                  <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>
                                    {c.doc_id} · Page {c.page_number}
                                    {c.section_header ? ` · ${c.section_header}` : ""}
                                  </div>
                                  <div style={{ fontSize: 11, color: "var(--text-dim)", marginTop: 3, lineHeight: 1.4 }}>
                                    {c.text_preview}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}

                {sending && (
                  <div className="fade-in" style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <div className="glass" style={{ padding: "14px 18px", display: "flex", gap: 8, alignItems: "center" }}>
                      <span className="spinner" />
                      <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Retrieving and generating...</span>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Chat input */}
              <div style={{ borderTop: "1px solid var(--border)", padding: "16px 20px" }}>
                <form onSubmit={handleSend} style={{ display: "flex", gap: "10px" }}>
                  <textarea
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(e as any); } }}
                    placeholder="Ask a question about your documents... (Enter to send)"
                    style={{ flex: 1, resize: "none", height: 46, paddingTop: 12 }}
                    rows={1}
                  />
                  <button className="btn btn-primary" type="submit" disabled={sending || !query.trim()} style={{ height: 46 }}>
                    {sending ? <span className="spinner" /> : "Send →"}
                  </button>
                </form>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
