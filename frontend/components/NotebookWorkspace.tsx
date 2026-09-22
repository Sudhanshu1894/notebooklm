"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { Notebook, Document, ChatResponse, Citation, api } from "@/lib/api";
import TeachingMessage from "./TeachingMessage";
import QuizMode from "./QuizMode";
import KnowledgeExplorer from "./KnowledgeExplorer";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Copy, Check, Volume2, VolumeX, Network, MessageSquare,
  Paperclip, ArrowUp, BookOpen, Brain, GraduationCap, Database,
  RotateCcw, Pencil, X, Trash2, FileText, FileSpreadsheet, Presentation, File,
  FileDown, ChevronDown, Loader2,
} from "lucide-react";

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
    window.speechSynthesis.cancel();
    if (speakingId === id) { setSpeakingId(null); return; }
    const clean = text
      .replace(/\[(\d+)\]\(#cite-\d+\)/g, "")
      .replace(/#{1,6}\s/g, "").replace(/\*\*/g, "").replace(/\*/g, "")
      .replace(/`{1,3}/g, "").replace(/>\s/g, "")
      .replace(/\n{2,}/g, ". ").replace(/\n/g, " ").trim();
    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.rate = 1.0; utterance.pitch = 1.0; utterance.volume = 1.0;
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

  const stop = useCallback(() => { window.speechSynthesis?.cancel(); setSpeakingId(null); }, []);
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

// ── Export Word (.docx) Button ────────────────────────────────────
function ExportDocxButton({
  notebookId,
  title,
  content,
  citations,
}: {
  notebookId: string;
  title: string;
  content: string;
  citations?: Citation[];
}) {
  const [downloading, setDownloading] = useState(false);

  const handleExport = async () => {
    setDownloading(true);
    try {
      await api.exportDocx(notebookId, {
        export_type: "answer",
        title: title || "Research Note",
        content,
        citations,
      });
    } catch (e) {
      console.error("Failed to export Word document:", e);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <button
      className="tts-btn"
      onClick={handleExport}
      disabled={downloading}
      title="Download as styled Microsoft Word (.docx)"
      style={{ display: "inline-flex", alignItems: "center", gap: 4, marginLeft: 2 }}
    >
      {downloading ? (
        <>
          <span className="spinner spinner-sm" style={{ width: 11, height: 11 }} />
          Exporting…
        </>
      ) : (
        <>
          <FileDown size={13} color="#4f46e5" />
          Word (.docx)
        </>
      )}
    </button>
  );
}

// ── Status badge ─────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  if (status === "ready")  return <span className="badge badge-ready">● Ready</span>;
  if (status === "failed") return <span className="badge badge-failed">✗ Failed</span>;
  return (
    <span className="badge badge-pending">
      <span className="spinner spinner-sm" /> Processing
    </span>
  );
}

// ── File-type icon ───────────────────────────────────────────────
function DocIcon({ filename }: { filename: string }) {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  const props = { size: 18, strokeWidth: 1.5 };
  if (ext === "pdf") return <FileText {...props} color="#ef4444" />;
  if (["docx", "doc"].includes(ext)) return <FileText {...props} color="#3b82f6" />;
  if (["pptx", "ppt"].includes(ext)) return <Presentation {...props} color="#f97316" />;
  if (["xlsx", "csv"].includes(ext)) return <FileSpreadsheet {...props} color="#22c55e" />;
  return <File {...props} color="var(--text-dim)" />;
}

// ── Lumina Avatar ────────────────────────────────────────────────
function LuminaAvatar({ size = 32 }: { size?: number }) {
  const iconSize = Math.round(size * 0.55);
  return (
    <div style={{
      width: size, height: size, borderRadius: size > 40 ? 14 : 8, flexShrink: 0,
      background: "linear-gradient(135deg, #6366f1 0%, #a855f7 60%, #ec4899 100%)",
      display: "flex", alignItems: "center", justifyContent: "center",
      boxShadow: `0 2px ${size > 40 ? "16px" : "8px"} rgba(99,102,241,0.35)`,
    }}>
      <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="none">
        <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill="white" opacity="0.95"/>
      </svg>
    </div>
  );
}

// ── Thinking timer ───────────────────────────────────────────────
function ThinkingIndicator() {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="fade-in" style={{ display: "flex", gap: 14, marginBottom: 28, width: "100%" }}>
      <LuminaAvatar size={32} />
      <div style={{ paddingTop: 6 }}>
        <div className="typing-dots"><span /><span /><span /></div>
        {elapsed >= 3 && (
          <div style={{ fontSize: 11, color: "var(--text-dim)", marginTop: 6, fontStyle: "italic" }}>
            {elapsed < 8 ? "Retrieving context…" : elapsed < 15 ? "Generating answer…" : `Still thinking… (${elapsed}s)`}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Dynamic suggestions ──────────────────────────────────────────
const SUGGESTED_NO_DOCS = [
  "Upload a PDF, DOCX, or PPTX to get started.",
  "Then ask me to teach you the main concepts.",
  "Or switch to the Quiz tab to test knowledge.",
  "Paste a YouTube link to discuss a video.",
];
const SUGGESTED_WITH_DOCS = [
  "Teach me the main concepts from this document.",
  "Explain how the key mechanism described here works.",
  "What are the key takeaways from this document?",
  "Give me an overview of the main topics covered.",
  "What questions does this document answer?",
  "Summarise this in 5 bullet points.",
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
  const [activeTab, setActiveTab] = useState<"chat" | "quiz" | "knowledge">("chat");
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [chatMode, setChatMode] = useState<"auto" | "teach">("auto");
  const [modelPreference, setModelPreference] = useState<"auto" | "gemini" | "local">("auto");
  const [editingMsgId, setEditingMsgId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState("");
  const [deletingDocId, setDeletingDocId] = useState<string | null>(null);
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportStatusText, setExportStatusText] = useState<string | null>(null);
  const exportMenuRef = useRef<HTMLDivElement>(null);

  const fileRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const editRef = useRef<HTMLTextAreaElement>(null);
  const pollingRef = useRef<Record<string, NodeJS.Timeout>>({});
  const { speakingId, speak } = useTTS();

  // Close export menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (exportMenuRef.current && !exportMenuRef.current.contains(event.target as Node)) {
        setExportMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleExportStudyGuide = async () => {
    setExporting(true);
    setExportMenuOpen(false);
    setExportStatusText("Synthesizing comprehensive Study Guide across all document topics...");
    try {
      await api.exportAutoStudyGuide(notebook.notebook_id, notebook.name);
      setExportStatusText("Study Guide (.docx) downloaded successfully!");
      setTimeout(() => setExportStatusText(null), 4000);
    } catch (err) {
      console.error("Export study guide error:", err);
      // Direct stream fallback via browser window
      try {
        const directUrl = api.getStudyGuideDownloadUrl(notebook.notebook_id);
        window.open(directUrl, "_blank");
        setExportStatusText("Download triggered via direct browser stream!");
        setTimeout(() => setExportStatusText(null), 4000);
      } catch (e2) {
        setExportStatusText("Failed to download study guide. Please try again.");
        setTimeout(() => setExportStatusText(null), 5000);
      }
    } finally {
      setExporting(false);
    }
  };

  const handleExportChat = async () => {
    setExporting(true);
    setExportMenuOpen(false);
    setExportStatusText("Generating Chat Transcript (.docx)...");
    try {
      await api.exportDocx(notebook.notebook_id, {
        export_type: "chat",
        title: notebook.name,
      });
      setExportStatusText("Chat Transcript (.docx) downloaded successfully!");
      setTimeout(() => setExportStatusText(null), 4000);
    } catch (err) {
      console.error("Export chat transcript error:", err);
      setExportStatusText("Failed to export chat transcript. Please try again.");
      setTimeout(() => setExportStatusText(null), 5000);
    } finally {
      setExporting(false);
    }
  };

  // Load data
  useEffect(() => {
    api.listSources(notebook.notebook_id).then((docs) => {
      setDocuments(docs);
      if (docs.length > 0) setSourcesOpen(true);
    }).catch(() => {});
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
    return () => { Object.values(pollingRef.current).forEach(clearInterval); };
  }, [notebook.notebook_id]);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, sending]);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 180) + "px";
  }, [query]);

  // Auto-resize edit textarea
  useEffect(() => {
    const ta = editRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
  }, [editDraft]);

  // Global keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Ctrl+/ or Cmd+/ — focus input
      if ((e.ctrlKey || e.metaKey) && e.key === "/") {
        e.preventDefault();
        textareaRef.current?.focus();
      }
      // Escape — clear input (if focused) or close edit mode
      if (e.key === "Escape") {
        if (editingMsgId) { setEditingMsgId(null); setEditDraft(""); return; }
        if (document.activeElement === textareaRef.current) setQuery("");
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [editingMsgId]);

  function pollDocument(docId: string) {
    const timer = setInterval(async () => {
      try {
        const doc = await api.getDocumentStatus(notebook.notebook_id, docId);
        setDocuments((prev) => prev.map((d) => d.doc_id === docId ? doc : d));
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
    setSourcesOpen(true); // auto-open sources panel on upload
    try {
      const res = await api.uploadDocument(notebook.notebook_id, file);
      const tempDoc: Document = {
        doc_id: res.doc_id, filename: file.name, status: "processing",
        chunk_count: 0, error_message: "", created_at: new Date().toISOString(), updated_at: new Date().toISOString()
      };
      setDocuments((p) => [tempDoc, ...p]);
      pollDocument(res.doc_id);
      if (onTitleChange) onTitleChange();
    } catch (err) { alert("Upload failed: " + err); }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = ""; }
  }

  async function handleDeleteDoc(docId: string) {
    setDeletingDocId(docId);
    try {
      await api.deleteDocument(notebook.notebook_id, docId);
      setDocuments((prev) => prev.filter((d) => d.doc_id !== docId));
    } catch (err) {
      console.error("Failed to delete doc:", err);
    } finally {
      setDeletingDocId(null);
    }
  }

  async function handleSend(e?: React.FormEvent, overrideQuery?: string) {
    e?.preventDefault();
    const q = (overrideQuery ?? query).trim();
    if (!q || sending) return;
    setQuery("");
    const userMsg: Message = { id: Date.now().toString(), role: "user", content: q };
    setMessages((p) => [...p, userMsg]);
    setSending(true);
    try {
      const result: ChatResponse = await api.chat(notebook.notebook_id, q, 5, chatMode, modelPreference);
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

  // Regenerate: removes last assistant message, re-sends last user message
  async function handleRegenerate() {
    if (sending) return;
    const last = [...messages].reverse().find((m) => m.role === "user");
    if (!last) return;
    // Remove all messages after and including the last assistant response
    setMessages((prev) => {
      const idx = prev.findLastIndex((m) => m.role === "assistant");
      return idx >= 0 ? prev.slice(0, idx) : prev;
    });
    setSending(true);
    try {
      const result: ChatResponse = await api.chat(notebook.notebook_id, last.content, 5, chatMode, modelPreference);
      setMessages((p) => [...p, {
        id: Date.now().toString(),
        role: "assistant",
        content: result.answer,
        citations: result.citations,
        route: result.route,
        is_insufficient: result.is_insufficient,
        mode_used: result.mode_used,
      }]);
    } catch (err) {
      setMessages((p) => [...p, { id: Date.now().toString(), role: "assistant", content: `Error: ${err}` }]);
    } finally { setSending(false); }
  }

  // Edit user message: re-sends edited version
  function startEdit(msg: Message) {
    setEditingMsgId(msg.id);
    setEditDraft(msg.content);
    setTimeout(() => editRef.current?.select(), 30);
  }

  async function commitEdit() {
    if (!editingMsgId || !editDraft.trim() || sending) return;
    const draft = editDraft.trim();
    // Replace user message + remove all subsequent messages
    setMessages((prev) => {
      const idx = prev.findIndex((m) => m.id === editingMsgId);
      if (idx < 0) return prev;
      return [...prev.slice(0, idx), { ...prev[idx], content: draft }];
    });
    setEditingMsgId(null);
    setEditDraft("");
    // Re-send
    setSending(true);
    try {
      const result: ChatResponse = await api.chat(notebook.notebook_id, draft, 5, chatMode, modelPreference);
      setMessages((p) => [...p, {
        id: Date.now().toString(),
        role: "assistant",
        content: result.answer,
        citations: result.citations,
        route: result.route,
        is_insufficient: result.is_insufficient,
        mode_used: result.mode_used,
      }]);
    } catch (err) {
      setMessages((p) => [...p, { id: Date.now().toString(), role: "assistant", content: `Error: ${err}` }]);
    } finally { setSending(false); }
  }

  const preprocessContent = (text: string) =>
    text.replace(/\[(\d+)\]/g, "[$1](#cite-$1)");

  const hasDocs = documents.length > 0;
  const suggestions = hasDocs ? SUGGESTED_WITH_DOCS : SUGGESTED_NO_DOCS;
  const charCount = query.length;
  const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
  const lastMsg = messages[messages.length - 1];
  const canRegenerate = !sending && lastMsg?.role === "assistant" && !!lastUserMsg;

  // Tab config
  const TABS = [
    { id: "chat", label: "Chat", icon: <MessageSquare size={13} /> },
    { id: "quiz", label: "Quiz", icon: <Brain size={13} /> },
    { id: "knowledge", label: "Knowledge", icon: <Database size={13} /> },
  ] as const;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden", background: "var(--bg-base)" }}>
      <input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.pptx,.ppt" style={{ display: "none" }} onChange={handleUpload} />

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
        <div style={{ display: "flex", gap: 4, background: "#f0ece6", borderRadius: 10, padding: 3, position: "relative" }}>
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "6px 14px", borderRadius: 8, border: "none", cursor: "pointer",
                fontSize: 13, fontWeight: 600,
                background: activeTab === tab.id ? "var(--bg-panel)" : "transparent",
                color: activeTab === tab.id ? "var(--text-primary)" : "var(--text-dim)",
                boxShadow: activeTab === tab.id ? "0 1px 4px rgba(0,0,0,0.08)" : "none",
                transition: "all 0.18s",
                position: "relative",
              }}
            >
              {tab.icon}
              {tab.label}
              {/* Active underline accent */}
              {activeTab === tab.id && (
                <span style={{
                  position: "absolute", bottom: 3, left: "50%",
                  transform: "translateX(-50%)",
                  width: 16, height: 2, borderRadius: 2,
                  background: "var(--accent)",
                  transition: "width 0.2s",
                }} />
              )}
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

        {/* Export Dropdown */}
        <div style={{ position: "relative" }} ref={exportMenuRef}>
          <button
            onClick={() => !exporting && setExportMenuOpen(!exportMenuOpen)}
            disabled={exporting}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "6px 14px", borderRadius: 8, border: "1px solid var(--border)",
              background: exporting ? "rgba(99,102,241,0.08)" : "var(--bg-panel)",
              color: exporting ? "#4f46e5" : "var(--text-secondary)",
              cursor: exporting ? "wait" : "pointer", fontSize: 13, fontWeight: 600,
              transition: "all 0.18s"
            }}
            title="Export research documents to Microsoft Word (.docx)"
          >
            {exporting ? (
              <>
                <Loader2 size={13} className="animate-spin" color="#4f46e5" />
                <span>Exporting...</span>
              </>
            ) : (
              <>
                <FileDown size={13} color="#4f46e5" />
                <span>Export (.docx)</span>
                <ChevronDown size={12} style={{ opacity: 0.7 }} />
              </>
            )}
          </button>

          {exportMenuOpen && (
            <div style={{
              position: "absolute", top: "calc(100% + 6px)", right: 0,
              background: "var(--bg-panel)", border: "1px solid var(--border)",
              borderRadius: 10, padding: 6, minWidth: 230,
              boxShadow: "0 8px 24px rgba(0,0,0,0.12)", zIndex: 100,
              display: "flex", flexDirection: "column", gap: 2,
            }}>
              <button
                onClick={handleExportStudyGuide}
                disabled={exporting}
                style={{
                  display: "flex", alignItems: "center", gap: 8,
                  padding: "8px 12px", borderRadius: 6, border: "none",
                  background: "transparent", color: "var(--text-primary)",
                  cursor: "pointer", fontSize: 13, textAlign: "left",
                  transition: "background 0.15s",
                }}
                onMouseOver={(e) => e.currentTarget.style.background = "var(--bg-user-msg)"}
                onMouseOut={(e) => e.currentTarget.style.background = "transparent"}
              >
                <FileText size={15} color="#4f46e5" />
                <div>
                  <div style={{ fontWeight: 600 }}>Study Guide (.docx)</div>
                  <div style={{ fontSize: 11, color: "var(--text-dim)" }}>Full synthesis with bibliography</div>
                </div>
              </button>

              <button
                onClick={handleExportChat}
                disabled={exporting || messages.length === 0}
                style={{
                  display: "flex", alignItems: "center", gap: 8,
                  padding: "8px 12px", borderRadius: 6, border: "none",
                  background: "transparent", color: messages.length === 0 ? "var(--text-dim)" : "var(--text-primary)",
                  cursor: messages.length === 0 ? "not-allowed" : "pointer", fontSize: 13, textAlign: "left",
                  transition: "background 0.15s",
                }}
                onMouseOver={(e) => { if (messages.length > 0) e.currentTarget.style.background = "var(--bg-user-msg)"; }}
                onMouseOut={(e) => e.currentTarget.style.background = "transparent"}
              >
                <MessageSquare size={15} color="#4338ca" />
                <div>
                  <div style={{ fontWeight: 600 }}>Chat Transcript (.docx)</div>
                  <div style={{ fontSize: 11, color: "var(--text-dim)" }}>All questions & cited answers</div>
                </div>
              </button>
            </div>
          )}
        </div>
      </header>

      {/* ── Body ───────────────────────────────────────────────── */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>

        {/* Center: Chat or Tabs */}
        <div style={{ flex: 1, position: "relative", overflow: "hidden", minWidth: 0 }}>
          {activeTab === "quiz" ? (
            <QuizMode notebookId={notebook.notebook_id} />
          ) : activeTab === "knowledge" ? (
            <KnowledgeExplorer notebookId={notebook.notebook_id} />
          ) : (
            <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>

              {/* Messages */}
              <div style={{
                flex: 1, overflowY: "auto", padding: "32px 20px 0",
                display: "flex", flexDirection: "column", alignItems: "center"
              }}>
                <div style={{ width: "100%", maxWidth: 760, display: "flex", flexDirection: "column", gap: 0, paddingBottom: 150 }}>

                  {/* Empty state */}
                  {messages.length === 0 && (
                    <div className="fade-in" style={{
                      display: "flex", flexDirection: "column",
                      alignItems: "center", justifyContent: "center",
                      gap: 12, minHeight: "55vh", paddingTop: "4vh"
                    }}>
                      <LuminaAvatar size={52} />
                      <h2 style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: 4 }}>
                        {hasDocs ? "What would you like to learn?" : "Get started"}
                      </h2>
                      <p style={{ color: "var(--text-dim)", fontSize: 14, textAlign: "center", maxWidth: 420, marginBottom: 24, lineHeight: 1.6 }}>
                        {hasDocs
                          ? `${documents.length} source${documents.length > 1 ? "s" : ""} ready. Ask a question or pick a suggestion below.`
                          : "Upload a document, then ask a question or say \"Teach me\" for a structured lesson."}
                      </p>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, width: "100%", maxWidth: 580 }}>
                        {suggestions.slice(0, 4).map((s) => (
                          <button
                            key={s}
                            className="prompt-card"
                            disabled={!hasDocs}
                            onClick={() => {
                              if (!hasDocs) { fileRef.current?.click(); return; }
                              setQuery(s);
                              if (s.toLowerCase().startsWith("teach")) setChatMode("teach");
                              textareaRef.current?.focus();
                            }}
                          >
                            <GraduationCap size={13} style={{ opacity: 0.6, flexShrink: 0 }} />
                            {s}
                          </button>
                        ))}
                      </div>
                      {!hasDocs && (
                        <button
                          className="btn btn-primary"
                          style={{ marginTop: 8, padding: "10px 22px", fontSize: 14 }}
                          onClick={() => fileRef.current?.click()}
                        >
                          <Paperclip size={14} /> Upload a document
                        </button>
                      )}
                    </div>
                  )}

                  {/* Message list */}
                  {messages.map((msg, idx) => (
                    <div key={msg.id} className="fade-in msg-group" style={{
                      display: "flex",
                      flexDirection: "column",
                      alignItems: msg.role === "user" ? "flex-end" : "flex-start",
                      marginBottom: msg.role === "user" ? 24 : 28,
                      width: "100%",
                    }}>
                      {msg.role === "user" ? (
                        /* User bubble */
                        <div style={{ maxWidth: "72%", display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
                          {editingMsgId === msg.id ? (
                            /* Inline edit */
                            <div style={{
                              background: "var(--bg-user-msg)", border: "1px solid var(--accent)",
                              borderRadius: "18px 18px 4px 18px", padding: "10px 14px",
                              width: "100%", boxShadow: "0 0 0 2px rgba(181,112,74,0.15)",
                            }}>
                              <textarea
                                ref={editRef}
                                value={editDraft}
                                onChange={(e) => setEditDraft(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); commitEdit(); }
                                  if (e.key === "Escape") { setEditingMsgId(null); setEditDraft(""); }
                                }}
                                style={{
                                  width: "100%", background: "transparent", border: "none", outline: "none",
                                  color: "var(--text-primary)", fontSize: 15, lineHeight: 1.6,
                                  fontFamily: "inherit", resize: "none", minHeight: 40,
                                }}
                                rows={1}
                                autoFocus
                              />
                              <div style={{ display: "flex", gap: 6, justifyContent: "flex-end", marginTop: 8 }}>
                                <button
                                  onClick={() => { setEditingMsgId(null); setEditDraft(""); }}
                                  style={{ padding: "4px 10px", borderRadius: 6, border: "1px solid var(--border)", background: "transparent", cursor: "pointer", fontSize: 12, color: "var(--text-dim)" }}
                                >
                                  Cancel
                                </button>
                                <button
                                  onClick={commitEdit}
                                  disabled={!editDraft.trim()}
                                  style={{
                                    padding: "4px 12px", borderRadius: 6, border: "none",
                                    background: "linear-gradient(135deg,#b5704a,#c97d50)",
                                    color: "#fff", cursor: "pointer", fontSize: 12, fontWeight: 600,
                                  }}
                                >
                                  Send
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div style={{
                              background: "var(--bg-user-msg)", color: "var(--text-primary)",
                              padding: "12px 18px",
                              borderRadius: "18px 18px 4px 18px",
                              fontSize: 15, lineHeight: 1.6,
                              border: "1px solid var(--border)",
                            }}>
                              {msg.content}
                            </div>
                          )}
                          {/* Edit button — show on last user message if not editing */}
                          {!editingMsgId && idx === messages.findLastIndex((m) => m.role === "user") && (
                            <button
                              onClick={() => startEdit(msg)}
                              style={{
                                display: "flex", alignItems: "center", gap: 4,
                                background: "none", border: "none", cursor: "pointer",
                                color: "var(--text-dim)", fontSize: 11.5, padding: "2px 4px",
                                borderRadius: 4, transition: "color 0.15s",
                              }}
                              onMouseOver={e => (e.currentTarget.style.color = "var(--text-secondary)")}
                              onMouseOut={e => (e.currentTarget.style.color = "var(--text-dim)")}
                              title="Edit message"
                            >
                              <Pencil size={11} /> Edit
                            </button>
                          )}
                        </div>
                      ) : (
                        /* AI response */
                        <div style={{ width: "100%", display: "flex", gap: 14 }}>
                          <LuminaAvatar size={32} />

                          <div style={{ flex: 1, minWidth: 0 }}>
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
                              {/* Regenerate — only on last assistant message */}
                              {idx === messages.length - 1 && canRegenerate && (
                                <button
                                  className="tts-btn"
                                  onClick={handleRegenerate}
                                  title="Regenerate response"
                                  style={{ marginLeft: 2 }}
                                >
                                  <RotateCcw size={13} /> Regenerate
                                </button>
                              )}
                              {/* Export as Word (.docx) */}
                              <ExportDocxButton
                                notebookId={notebook.notebook_id}
                                title={
                                  messages[idx - 1]?.role === "user"
                                    ? messages[idx - 1].content
                                    : `${notebook.name} — Note`
                                }
                                content={msg.content}
                                citations={msg.citations}
                              />
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Thinking indicator */}
                  {sending && <ThinkingIndicator />}

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
                      {/* Attach */}
                      <button
                        type="button" className="btn-icon"
                        style={{ marginBottom: 4, flexShrink: 0 }}
                        onClick={() => fileRef.current?.click()}
                        title={uploading ? "Uploading..." : "Attach document (PDF, DOCX, PPTX, TXT)"}
                        disabled={uploading}
                      >
                        {uploading ? <span className="spinner spinner-sm" /> : <Paperclip size={16} />}
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
                        Teach
                      </button>

                      {/* Model toggle */}
                      <select
                        value={modelPreference}
                        onChange={(e) => setModelPreference(e.target.value as "auto" | "gemini" | "local")}
                        title="Select Model"
                        style={{
                          marginBottom: 4, flexShrink: 0,
                          padding: "5px 10px", borderRadius: 7, border: "1px solid var(--border)",
                          background: "var(--bg-panel)", color: "var(--text-primary)",
                          fontSize: 11.5, fontWeight: 600, cursor: "pointer", outline: "none",
                        }}
                      >
                        <option value="auto">Auto Model</option>
                        <option value="gemini">Gemini</option>
                        <option value="local">Local SLM</option>
                      </select>

                      <textarea
                        ref={textareaRef}
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
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

                      {/* Char counter — shown when > 200 chars */}
                      {charCount > 200 && (
                        <span style={{
                          fontSize: 10.5, color: charCount > 2000 ? "#ef4444" : "var(--text-dim)",
                          flexShrink: 0, marginBottom: 6, lineHeight: 1,
                          fontVariantNumeric: "tabular-nums",
                        }}>
                          {charCount}
                        </span>
                      )}

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
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, padding: "0 4px" }}>
                    <span style={{ fontSize: 11, color: "var(--text-dim)" }}>
                      <kbd style={{ fontSize: 10, padding: "1px 4px", borderRadius: 3, border: "1px solid var(--border)", background: "var(--bg-panel)" }}>Ctrl+/</kbd> focus · <kbd style={{ fontSize: 10, padding: "1px 4px", borderRadius: 3, border: "1px solid var(--border)", background: "var(--bg-panel)" }}>Esc</kbd> clear
                    </span>
                    <span style={{ fontSize: 11, color: "var(--text-dim)" }}>
                      AI can make mistakes. Verify important information.
                    </span>
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
              {/* Panel header */}
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

              {/* Doc list */}
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
                    <div
                      key={doc.doc_id}
                      className="doc-card"
                      style={{ position: "relative", paddingRight: 36 }}
                    >
                      <DocIcon filename={doc.filename} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{
                          fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)",
                          whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                          marginBottom: 4
                        }} title={doc.filename}>
                          {doc.filename}
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <StatusBadge status={doc.status} />
                          {doc.chunk_count > 0 && (
                            <span style={{ fontSize: 10.5, color: "var(--text-dim)" }}>
                              {doc.chunk_count} chunk{doc.chunk_count !== 1 ? "s" : ""}
                            </span>
                          )}
                        </div>
                      </div>
                      {/* Delete doc button */}
                      <button
                        onClick={() => handleDeleteDoc(doc.doc_id)}
                        disabled={deletingDocId === doc.doc_id}
                        title="Remove source"
                        style={{
                          position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)",
                          background: "none", border: "none", cursor: "pointer",
                          color: "var(--text-dim)", padding: 4, borderRadius: 5,
                          display: "flex", alignItems: "center",
                          opacity: deletingDocId === doc.doc_id ? 0.4 : 0.6,
                          transition: "opacity 0.15s, color 0.15s",
                        }}
                        onMouseOver={e => (e.currentTarget.style.color = "#ef4444", e.currentTarget.style.opacity = "1")}
                        onMouseOut={e => (e.currentTarget.style.color = "var(--text-dim)", e.currentTarget.style.opacity = "0.6")}
                      >
                        {deletingDocId === doc.doc_id
                          ? <span className="spinner spinner-sm" />
                          : <Trash2 size={13} />
                        }
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Floating Export Status Toast */}
      {exportStatusText && (
        <div style={{
          position: "fixed", bottom: 28, right: 28, zIndex: 9999,
          background: "var(--bg-panel)",
          border: exporting ? "1px solid #6366f1" : "1px solid #10b981",
          borderRadius: 12, padding: "12px 20px",
          boxShadow: "0 12px 32px rgba(0,0,0,0.18)",
          display: "flex", alignItems: "center", gap: 12,
          color: "var(--text-primary)", fontSize: 13.5, fontWeight: 500,
          animation: "fadeIn 0.2s ease-out",
        }}>
          {exporting ? (
            <Loader2 size={18} className="animate-spin" color="#6366f1" />
          ) : (
            <Check size={18} color="#10b981" />
          )}
          <span>{exportStatusText}</span>
        </div>
      )}
    </div>
  );
}
