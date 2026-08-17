"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { Notebook, Document, ChatResponse, Citation, api } from "@/lib/api";
import GraphExplorer from "./GraphExplorer";
import TeachingMessage from "./TeachingMessage";
import QuizMode from "./QuizMode";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Check, Volume2, VolumeX, Network, MessageSquare, Paperclip, ArrowUp, BookOpen, Brain, GraduationCap } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  route?: string;
  is_insufficient?: boolean;
  new_title?: string;
  mode_used?: string;
}

// ── TTS hook ────────────────────────────────────────────────────
function useTTS() {
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  const speak = useCallback((id: string, text: string) => {
    if (typeof window === "undefined" || !window.speechSynthesis) return;
    // Stop current speech
    window.speechSynthesis.cancel();
    if (speakingId === id) { setSpeakingId(null); return; }

    // Strip markdown symbols for cleaner audio
    const clean = text
      .replace(/\[(\d+)\]\(#cite-\d+\)/g, "")
      .replace(/#{1,6}\s/g, "")
      .replace(/\*\*/g, "")
      .replace(/\*/g, "")
      .replace(/`{1,3}/g, "")
      .replace(/>\s/g, "")
      .replace(/\n{2,}/g, ". ")
      .replace(/\n/g, " ")
      .trim();

    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    // Prefer a natural-sounding voice
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(
      (v) => v.lang.startsWith("en") && (v.name.includes("Natural") || v.name.includes("Neural") || v.name.includes("Google"))
    ) || voices.find((v) => v.lang.startsWith("en"));
    if (preferred) utterance.voice = preferred;

    utterance.onend = () => setSpeakingId(null);
    utterance.onerror = () => setSpeakingId(null);
    utteranceRef.current = utterance;
    setSpeakingId(id);
    window.speechSynthesis.speak(utterance);
  }, [speakingId]);

  const stop = useCallback(() => {
    window.speechSynthesis?.cancel();
    setSpeakingId(null);
  }, []);

  // Stop TTS when component unmounts
  useEffect(() => () => { window.speechSynthesis?.cancel(); }, []);

  return { speakingId, speak, stop };
}

// ── Copy button ──────────────────────────────────────────────────
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <button className="btn-icon" onClick={copy} title={copied ? "Copied!" : "Copy response"}>
      {copied ? <Check size={14} strokeWidth={2.5} color="var(--success)" /> : <Copy size={14} />}
    </button>
  );
}

// ── Status badge ─────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  if (status === "ready")   return <span className="badge badge-ready">● Ready</span>;
  if (status === "failed")  return <span className="badge badge-failed">✗ Failed</span>;
  return (
    <span className="badge badge-pending">
      <span className="spinner spinner-sm" /> Processing
    </span>
  );
}

const SUGGESTED = [
  "Teach me the main concepts from this document.",
  "Explain how the key mechanism described here works.",
  "What are the key takeaways from this document?",
  "Give me an overview of the main topics covered.",
];

// ── Main Component ───────────────────────────────────────────────
export default function NotebookWorkspace({
  notebook, onBack, onTitleChange
}: {
  notebook: Notebook;
  onBack: () => void;
  onTitleChange?: () => void;
}) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [query, setQuery] = useState("");
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [activeTab, setActiveTab] = useState<"chat" | "graph" | "quiz">("chat");
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [chatMode, setChatMode] = useState<"auto" | "teach">("auto");

  const fileRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const pollingRef = useRef<Record<string, NodeJS.Timeout>>({});
  const { speakingId, speak } = useTTS();

  // Load data
  useEffect(() => {
    api.listSources(notebook.notebook_id).then(setDocuments).catch(() => {});
    api.listMessages(notebook.notebook_id).then((history) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setMessages(history.map((msg: any) => ({
        id: msg.message_id,
        role: msg.role as "user" | "assistant",
        content: msg.content,
        citations: msg.citations,
        route: msg.route,
        is_insufficient: msg.is_insufficient,
      })));
    }).catch(() => {});
    return () => {
      const p = pollingRef.current;
      Object.values(p).forEach(clearInterval);
    };
  }, [notebook.notebook_id]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 180) + "px";
  }, [query]);

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
      const tempDoc: Document = {
        doc_id: res.doc_id, filename: file.name, status: "processing",
        chunk_count: 0, error_message: "", created_at: new Date().toISOString(), updated_at: new Date().toISOString()
      };
      setDocuments((p) => [tempDoc, ...p]);
      pollDocument(res.doc_id);
    } catch (err) { alert("Upload failed: " + err); }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = ""; }
  }

  async function handleSend(e?: React.FormEvent) {
    e?.preventDefault();
    if (!query.trim() || sending) return;
    const q = query.trim();
    setQuery("");
    const userMsg: Message = { id: Date.now().toString(), role: "user", content: q };
    setMessages((p) => [...p, userMsg]);
    setSending(true);
    try {
      const result: ChatResponse = await api.chat(notebook.notebook_id, q, 5, chatMode);
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: result.answer,
        citations: result.citations,
        route: result.route,
        is_insufficient: result.is_insufficient,
        mode_used: result.mode_used,
      };
      setMessages((p) => [...p, assistantMsg]);
      if (result.new_title && onTitleChange) onTitleChange();
    } catch (err) {
      setMessages((p) => [...p, { id: Date.now().toString(), role: "assistant", content: `Error: ${err}` }]);
    } finally { setSending(false); }
  }

  const preprocessContent = (text: string) =>
    text.replace(/\[(\d+)\]/g, "[$1](#cite-$1)");

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden", background: "var(--bg-base)" }}>
      {/* Always-mounted file input — shared by chat bar and Sources panel */}
      <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" style={{ display: "none" }} onChange={handleUpload} />

      {/* ── Header ─────────────────────────────────────────────── */}
      <header style={{
        padding: "14px 20px 14px 60px",
        display: "flex", alignItems: "center", gap: 12,
        background: "var(--bg-base)",
        borderBottom: "1px solid var(--border)",
        flexShrink: 0, zIndex: 10
      }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 15, color: "var(--text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {notebook.name}
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 4, background: "#f0ece6", borderRadius: 10, padding: 3 }}>
          {(["chat", "quiz", "graph"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "6px 14px", borderRadius: 8, border: "none", cursor: "pointer",
                fontSize: 13, fontWeight: 600,
                background: activeTab === tab ? "var(--bg-panel)" : "transparent",
                color: activeTab === tab ? "var(--text-primary)" : "var(--text-dim)",
                boxShadow: activeTab === tab ? "0 1px 4px rgba(0,0,0,0.08)" : "none",
                transition: "all 0.18s",
              }}
            >
              {tab === "chat" ? <MessageSquare size={13} /> : tab === "quiz" ? <Brain size={13} /> : <Network size={13} />}
              {tab === "chat" ? "Chat" : tab === "quiz" ? "Quiz" : "Graph"}
            </button>
          ))}
        </div>

        {/* Sources toggle */}
        <button
          onClick={() => setSourcesOpen(!sourcesOpen)}
          style={{
            display: "flex", alignItems: "center", gap: 6,
            padding: "6px 14px", borderRadius: 8, border: "1px solid var(--border)",
            background: sourcesOpen ? "var(--accent-dim)" : "var(--bg-panel)",
            color: sourcesOpen ? "var(--accent)" : "var(--text-secondary)",
            cursor: "pointer", fontSize: 13, fontWeight: 600,
            transition: "all 0.18s"
          }}
        >
          <BookOpen size={13} />
          Sources {documents.length > 0 && <span style={{ fontSize: 11, opacity: 0.8 }}>({documents.length})</span>}
        </button>
      </header>

      {/* ── Body ───────────────────────────────────────────────── */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>

        {/* Center: Chat or Graph */}
        <div style={{ flex: 1, position: "relative", overflow: "hidden", minWidth: 0 }}>
          {activeTab === "graph" ? (
            <GraphExplorer notebookId={notebook.notebook_id} />
          ) : activeTab === "quiz" ? (
            <QuizMode notebookId={notebook.notebook_id} />
          ) : (
            <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>

              {/* Messages */}
              <div style={{
                flex: 1, overflowY: "auto", padding: "32px 20px 0",
                display: "flex", flexDirection: "column", alignItems: "center"
              }}>
                <div style={{ width: "100%", maxWidth: 760, display: "flex", flexDirection: "column", gap: 0, paddingBottom: 140 }}>

                  {/* Empty state */}
                  {messages.length === 0 && (
                    <div className="fade-in" style={{
                      display: "flex", flexDirection: "column",
                      alignItems: "center", justifyContent: "center",
                      gap: 12, minHeight: "55vh", paddingTop: "4vh"
                    }}>
                      <div style={{
                        width: 52, height: 52, borderRadius: 14,
                        background: "linear-gradient(135deg, #b5704a, #c97d50)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 24, marginBottom: 8,
                        boxShadow: "0 8px 24px rgba(181,112,74,0.25)"
                      }}>⬡</div>
                      <h2 style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: 4 }}>
                        What would you like to learn today?
                      </h2>
                      <p style={{ color: "var(--text-dim)", fontSize: 14, textAlign: "center", maxWidth: 420, marginBottom: 24, lineHeight: 1.6 }}>
                        Upload a document, then ask a question or say &quot;Teach me&quot; for a structured lesson with examples.
                        Switch to the <strong>Quiz</strong> tab to test your knowledge.
                      </p>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, width: "100%", maxWidth: 560 }}>
                        {SUGGESTED.map((q) => (
                          <button
                            key={q}
                            className="prompt-card"
                            onClick={() => { setQuery(q); setChatMode("teach"); textareaRef.current?.focus(); }}
                          >
                            <GraduationCap size={13} style={{ opacity: 0.6, flexShrink: 0 }} />
                            {q}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Message list */}
                  {messages.map((msg) => (
                    <div key={msg.id} className="fade-in msg-group" style={{
                      display: "flex",
                      flexDirection: "column",
                      alignItems: msg.role === "user" ? "flex-end" : "flex-start",
                      marginBottom: msg.role === "user" ? 24 : 28,
                      width: "100%",
                    }}>
                      {msg.role === "user" ? (
                        /* User bubble */
                        <div style={{
                          background: "var(--bg-user-msg)",
                          color: "var(--text-primary)",
                          padding: "12px 18px",
                          borderRadius: "18px 18px 4px 18px",
                          maxWidth: "72%",
                          fontSize: 15, lineHeight: 1.6,
                          border: "1px solid var(--border)",
                        }}>
                          {msg.content}
                        </div>
                      ) : (
                        /* AI response */
                        <div style={{ width: "100%", display: "flex", gap: 14 }}>
                          {/* Avatar */}
                          <div style={{
                            width: 32, height: 32, borderRadius: 8, flexShrink: 0,
                            background: "linear-gradient(135deg, #b5704a, #c97d50)",
                            display: "flex", alignItems: "center", justifyContent: "center",
                            color: "#fff", fontSize: 14, fontWeight: 700, marginTop: 2,
                            boxShadow: "0 2px 8px rgba(181,112,74,0.25)"
                          }}>⬡</div>

                          <div style={{ flex: 1, minWidth: 0 }}>
                            {/* Teaching mode: structured card layout */}
                            {msg.mode_used === "teach" ? (
                              <div style={{ paddingTop: 4 }}>
                                <TeachingMessage
                                  content={msg.content}
                                  citations={msg.citations || []}
                                  onCitationClick={setActiveCitation}
                                  activeCitationNum={activeCitation?.citation_number}
                                />
                              </div>
                            ) : (
                              /* Standard markdown content */
                              <div className="markdown-body" style={{ paddingTop: 4 }}>
                                <ReactMarkdown
                                  remarkPlugins={[remarkGfm]}
                                  components={{
                                    a: ({ href, children, ...props }) => {
                                      if (href?.startsWith("#cite-")) {
                                        const num = parseInt(href.replace("#cite-", ""));
                                        const cit = msg.citations?.find((c) => c.citation_number === num);
                                        return (
                                          <span
                                            className={`citation-pill ${activeCitation?.citation_number === num ? "active" : ""}`}
                                            onClick={() => setActiveCitation(cit === activeCitation ? null : cit || null)}
                                            title={cit?.text_preview || ""}
                                          >{num}</span>
                                        );
                                      }
                                      return <a href={href ?? ""} {...props} target="_blank" rel="noreferrer">{children}</a>;
                                    },
                                  }}
                                >
                                  {preprocessContent(msg.content)}
                                </ReactMarkdown>
                              </div>
                            )}

                            {/* Route badge */}
                            {msg.route && (
                              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 10 }}>
                                <span className={`badge ${msg.route === "hybrid" ? "badge-graph" : "badge-vector"}`}>
                                  {msg.route === "hybrid" ? "⬡ Graph + Vector" : "⬥ Vector only"}
                                </span>
                                {msg.is_insufficient && <span className="badge badge-failed">⚠ Insufficient context</span>}
                              </div>
                            )}

                            {/* Citations */}
                            {msg.citations && msg.citations.length > 0 && (
                              <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 6 }}>
                                <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 2 }}>
                                  Sources
                                </div>
                                {msg.citations.map((c) => (
                                  <div
                                    key={c.citation_number}
                                    className={`doc-card ${activeCitation?.citation_number === c.citation_number ? "glass-accent" : ""}`}
                                    onClick={() => setActiveCitation(activeCitation?.citation_number === c.citation_number ? null : c)}
                                    style={{ cursor: "pointer" }}
                                  >
                                    <span className="citation-pill" style={{ cursor: "default" }}>{c.citation_number}</span>
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                      <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>
                                        {c.doc_id} · Page {c.page_number}
                                        {c.section_header ? ` · ${c.section_header}` : ""}
                                      </div>
                                      <div style={{ fontSize: 11.5, color: "var(--text-dim)", marginTop: 3, lineHeight: 1.5 }}>
                                        {c.text_preview}
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Message actions */}
                            <div className="msg-actions">
                              <CopyButton text={msg.content} />
                              <button
                                className={`tts-btn ${speakingId === msg.id ? "speaking" : ""}`}
                                onClick={() => speak(msg.id, msg.content)}
                                title={speakingId === msg.id ? "Stop reading" : "Read aloud"}
                              >
                                {speakingId === msg.id
                                  ? <><VolumeX size={13} /> Stop</>
                                  : <><Volume2 size={13} /> Read aloud</>
                                }
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Thinking indicator */}
                  {sending && (
                    <div className="fade-in" style={{ display: "flex", gap: 14, marginBottom: 28, width: "100%" }}>
                      <div style={{
                        width: 32, height: 32, borderRadius: 8, flexShrink: 0,
                        background: "linear-gradient(135deg, #b5704a, #c97d50)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        color: "#fff", fontSize: 14, fontWeight: 700,
                      }}>⬡</div>
                      <div style={{ paddingTop: 8 }}>
                        <div className="typing-dots">
                          <span /><span /><span />
                        </div>
                      </div>
                    </div>
                  )}

                  <div ref={chatEndRef} />
                </div>
              </div>

              {/* ── Input bar ─────────────────────────────────── */}
              <div style={{
                position: "absolute", bottom: 0, left: 0, right: 0,
                padding: "16px 20px 20px",
                display: "flex", justifyContent: "center",
                background: "linear-gradient(to top, var(--bg-base) 60%, transparent)",
              }}>
                <div style={{ width: "100%", maxWidth: 760 }}>
                  <form onSubmit={handleSend}>
                    <div className="chat-input-wrap" style={{ padding: "8px 8px 8px 14px", display: "flex", alignItems: "flex-end", gap: 8 }}>
                      <button
                        type="button"
                        className="btn-icon"
                        style={{ marginBottom: 4, flexShrink: 0 }}
                        onClick={() => fileRef.current?.click()}
                        title={uploading ? "Uploading..." : "Attach document"}
                        disabled={uploading}
                      >
                        {uploading
                          ? <span className="spinner spinner-sm" />
                          : <Paperclip size={16} />
                        }
                      </button>

                      {/* Teach Me toggle */}
                      <button
                        type="button"
                        onClick={() => setChatMode((m) => m === "teach" ? "auto" : "teach")}
                        title={chatMode === "teach" ? "Teaching mode ON — click to switch to Chat" : "Switch to Teaching mode"}
                        style={{
                          marginBottom: 4, flexShrink: 0,
                          display: "flex", alignItems: "center", gap: 4,
                          padding: "5px 10px", borderRadius: 7, border: "none",
                          background: chatMode === "teach"
                            ? "linear-gradient(135deg,#6366f1,#8b5cf6)"
                            : "var(--border)",
                          color: chatMode === "teach" ? "#fff" : "var(--text-dim)",
                          fontSize: 11.5, fontWeight: 700, cursor: "pointer",
                          transition: "all 0.18s",
                          boxShadow: chatMode === "teach" ? "0 2px 8px rgba(99,102,241,0.35)" : "none",
                        }}
                      >
                        <GraduationCap size={13} />
                        {chatMode === "teach" ? "Teach" : "Teach"}
                      </button>

                      <textarea
                        ref={textareaRef}
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault();
                            handleSend();
                          }
                        }}
                        placeholder="Ask anything about your documents… (Shift+Enter for new line)"
                        style={{
                          flex: 1, resize: "none", minHeight: 40, maxHeight: 180,
                          padding: "9px 4px", background: "transparent", border: "none",
                          boxShadow: "none", fontSize: 15, outline: "none",
                          lineHeight: 1.5, color: "var(--text-primary)", fontFamily: "inherit",
                        }}
                        rows={1}
                      />

                      <button
                        type="submit"
                        disabled={sending || !query.trim()}
                        style={{
                          width: 36, height: 36, borderRadius: 8, border: "none",
                          background: query.trim() && !sending
                            ? "linear-gradient(135deg, #b5704a, #c97d50)"
                            : "var(--border)",
                          color: query.trim() && !sending ? "#fff" : "var(--text-dim)",
                          cursor: query.trim() && !sending ? "pointer" : "not-allowed",
                          display: "flex", alignItems: "center", justifyContent: "center",
                          flexShrink: 0, marginBottom: 2, transition: "all 0.2s",
                          boxShadow: query.trim() && !sending ? "0 2px 8px rgba(181,112,74,0.3)" : "none",
                        }}
                      >
                        {sending
                          ? <span className="spinner spinner-sm" style={{ borderTopColor: "#fff" }} />
                          : <ArrowUp size={16} strokeWidth={2.5} />
                        }
                      </button>
                    </div>
                  </form>
                  <div style={{ textAlign: "center", marginTop: 8, fontSize: 11, color: "var(--text-dim)" }}>
                    AI can make mistakes. Verify important information.
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Sources panel ───────────────────────────────────── */}
        {sourcesOpen && (
          <div className="fade-in" style={{
            width: 300, flexShrink: 0, padding: "16px 16px 16px 0",
            borderLeft: "1px solid var(--border)",
            display: "flex", flexDirection: "column",
            background: "var(--bg-base)",
          }}>
            <div style={{
              background: "var(--bg-panel)", borderRadius: 14,
              border: "1px solid var(--border)",
              height: "100%", display: "flex", flexDirection: "column", overflow: "hidden",
              boxShadow: "0 4px 16px rgba(0,0,0,0.04)"
            }}>
              <div style={{
                padding: "14px 16px", borderBottom: "1px solid var(--border)",
                display: "flex", alignItems: "center", gap: 8
              }}>
                <BookOpen size={15} color="var(--accent)" />
                <span style={{ fontSize: 13.5, fontWeight: 700, color: "var(--text-primary)" }}>
                  Sources ({documents.length})
                </span>
                <button
                  onClick={() => fileRef.current?.click()}
                  style={{
                    marginLeft: "auto", display: "flex", alignItems: "center", gap: 5,
                    background: "var(--accent-dim)", border: "none", borderRadius: 6,
                    color: "var(--accent)", padding: "5px 10px", cursor: "pointer",
                    fontSize: 12, fontWeight: 600
                  }}
                >
                  <Paperclip size={11} /> Add
                </button>
              </div>

              <div style={{ padding: "10px 12px", overflowY: "auto", flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
                {documents.length === 0 ? (
                  <div style={{
                    flex: 1, display: "flex", flexDirection: "column",
                    alignItems: "center", justifyContent: "center",
                    color: "var(--text-dim)", fontSize: 13, gap: 8, padding: "32px 16px"
                  }}>
                    <BookOpen size={28} strokeWidth={1.5} opacity={0.4} />
                    <span style={{ textAlign: "center", lineHeight: 1.5 }}>
                      No documents yet.<br />Upload a PDF, DOCX, or TXT.
                    </span>
                    <button
                      className="btn btn-primary"
                      style={{ padding: "8px 16px", fontSize: 13, marginTop: 4 }}
                      onClick={() => fileRef.current?.click()}
                    >
                      <Paperclip size={13} /> Upload
                    </button>
                  </div>
                ) : (
                  documents.map((doc) => (
                    <div key={doc.doc_id} className="doc-card">
                      <div style={{ fontSize: 20 }}>📄</div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{
                          fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)",
                          whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                          marginBottom: 4
                        }} title={doc.filename}>
                          {doc.filename}
                        </div>
                        <StatusBadge status={doc.status} />
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
