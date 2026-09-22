// Central API client for GraphRAG backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export interface Notebook {
  notebook_id: string;
  name: string;
  description: string;
  created_at?: string;
  is_pinned?: boolean;
}

export interface Document {
  doc_id: string;
  filename: string;
  status: string;
  chunk_count: number;
  error_message: string;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  citation_number: number;
  chunk_id: string;
  doc_id: string;
  page_number: number | string;
  section_header: string;
  text_preview: string;
}

export interface ChatResponse {
  query: string;
  answer: string;
  citations: Citation[];
  route: string;
  is_insufficient: boolean;
  new_title?: string;
  mode_used?: string;
}

export interface GraphData {
  nodes: { id: string; name: string; type: string; source_chunk_ids: string[] }[];
  edges: { source: string; target: string; label: string; description: string }[];
  demo_mode?: boolean;
  error?: string;
}

export interface QuizQuestion {
  type?: "mcq" | "fill_in_blank" | "short_answer";
  question: string;
  options?: string[];
  correct_index?: number;
  correct_answer?: string;
  grading_rubric?: string;
  explanation: string;
  source_hint?: string;
  difficulty?: "easy" | "medium" | "hard";
  topic?: string;
}

export interface QuizResponse {
  questions: QuizQuestion[];
  error?: string;
}

export interface KnowledgeItem {
  id: number;
  notebook_id: string;
  doc_id: string;
  knowledge_type: "summary" | "entity" | "concept" | "fact";
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface KnowledgeStats {
  notebook_id: string;
  documents_trained: number;
  total_items: number;
  by_type: Record<string, number>;
  ollama_model: string | null;
  ollama_available: boolean;
}

export const api = {

  async createNotebook(name: string = "New Research", userId: string = "anonymous"): Promise<{ notebook_id: string }> {
    const res = await fetch(`${API_BASE}/notebooks`, { 
      method: "POST",
      headers: { "Content-Type": "application/json", "X-User-Id": userId },
      body: JSON.stringify({ name, description: "" })
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async deleteNotebook(notebookId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/notebooks/${notebookId}`, { method: "DELETE" });
    if (!res.ok) throw new Error(await res.text());
  },

  async renameNotebook(notebookId: string, name: string): Promise<{ name: string }> {
    const res = await fetch(`${API_BASE}/notebooks/${notebookId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async pinNotebook(notebookId: string, is_pinned: boolean): Promise<void> {
    const res = await fetch(`${API_BASE}/notebooks/${notebookId}/pin`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_pinned }),
    });
    if (!res.ok) throw new Error(await res.text());
  },

  async listNotebooks(userId: string = "anonymous"): Promise<Notebook[]> {
    const res = await fetch(`${API_BASE}/notebooks`, {
      headers: { "X-User-Id": userId }
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async uploadDocument(notebookId: string, file: File): Promise<{ doc_id: string; status: string }> {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/notebooks/${notebookId}/documents`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getDocumentStatus(notebookId: string, docId: string): Promise<Document> {
    const res = await fetch(`${API_BASE}/notebooks/${notebookId}/documents/${docId}/status`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async listSources(notebookId: string): Promise<Document[]> {
    const res = await fetch(`${API_BASE}/notebooks/${notebookId}/sources`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async deleteDocument(notebookId: string, docId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/notebooks/${notebookId}/documents/${docId}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error(await res.text());
  },

  async chat(notebookId: string, query: string, topK = 5, mode: "auto" | "chat" | "teach" = "auto", modelPreference: string = "auto"): Promise<ChatResponse> {
    const res = await fetch(`${API_BASE}/notebooks/${notebookId}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: topK, mode, model_preference: modelPreference }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async generateQuiz(notebookId: string, topic = "", topK = 20, focusTopics?: string[]): Promise<QuizResponse> {
    const body: any = { topic, top_k: topK };
    if (focusTopics && focusTopics.length > 0) {
      body.focus_topics = focusTopics;
    }
    const res = await fetch(`${API_BASE}/notebooks/${notebookId}/quiz`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async recordQuizResult(notebookId: string, topic: string, isCorrect: boolean): Promise<void> {
    const res = await fetch(`${API_BASE}/notebooks/${notebookId}/quiz/results`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, is_correct: isCorrect }),
    });
    if (!res.ok) throw new Error(await res.text());
  },

  async gradeShortAnswer(notebookId: string, question: string, userAnswer: string, gradingRubric: string): Promise<{is_correct: boolean, feedback: string}> {
    const res = await fetch(`${API_BASE}/notebooks/${notebookId}/quiz/grade`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, user_answer: userAnswer, grading_rubric: gradingRubric }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async listMessages(notebookId: string): Promise<Record<string, unknown>[]> {
    const res = await fetch(`${API_BASE}/notebooks/${notebookId}/messages`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getGraph(notebookId: string): Promise<GraphData> {
    const res = await fetch(`${API_BASE}/notebooks/${notebookId}/graph`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async buildGraph(notebookId: string): Promise<{ status: string; documents: number }> {
    const res = await fetch(`${API_BASE}/notebooks/${notebookId}/build-graph`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getKnowledge(notebookId: string, type?: string): Promise<{ items: KnowledgeItem[]; count: number }> {
    const url = type
      ? `${API_BASE}/notebooks/${notebookId}/knowledge?knowledge_type=${type}`
      : `${API_BASE}/notebooks/${notebookId}/knowledge`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getKnowledgeStats(notebookId: string): Promise<KnowledgeStats> {
    const res = await fetch(`${API_BASE}/notebooks/${notebookId}/knowledge/stats`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getSystemPrompt(notebookId: string): Promise<{ system_prompt: string }> {
    const res = await fetch(`${API_BASE}/notebooks/${notebookId}/knowledge/system-prompt`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  getStudyGuideDownloadUrl(notebookId: string): string {
    return `${API_BASE}/notebooks/${notebookId}/export/study-guide`;
  },

  async exportDocx(
    notebookId: string,
    options: {
      export_type?: "answer" | "study_guide" | "chat";
      title?: string;
      content?: string;
      citations?: Citation[];
      takeaways?: string[];
    }
  ): Promise<void> {
    const res = await fetch(`${API_BASE}/notebooks/${notebookId}/export/docx`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(options),
    });
    if (!res.ok) throw new Error(await res.text());

    let filename = `${options.title || "Research_Export"}.docx`;
    const disposition = res.headers.get("Content-Disposition") || res.headers.get("content-disposition");
    if (disposition && disposition.includes("filename=")) {
      const match = disposition.match(/filename="?([^";]+)"?/);
      if (match && match[1]) filename = match[1].replace(/['"]/g, "").trim();
    }

    const blob = await res.blob();
    this.triggerDownload(blob, filename);
  },

  async exportAutoStudyGuide(notebookId: string, fallbackName = "Study_Guide"): Promise<void> {
    const res = await fetch(`${API_BASE}/notebooks/${notebookId}/export/study-guide`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(await res.text());

    let filename = `${fallbackName}_Study_Guide.docx`;
    const disposition = res.headers.get("Content-Disposition") || res.headers.get("content-disposition");
    if (disposition && disposition.includes("filename=")) {
      const match = disposition.match(/filename="?([^";]+)"?/);
      if (match && match[1]) filename = match[1].replace(/['"]/g, "").trim();
    }

    const blob = await res.blob();
    this.triggerDownload(blob, filename);
  },

  triggerDownload(blob: Blob, filename: string): void {
    const cleanName = filename.replace(/[^\w\.\-\s]/g, "_").trim() || "Research_Export.docx";
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = url;
    a.setAttribute("download", cleanName);
    document.body.appendChild(a);
    a.click();

    // Critical for Windows/Chrome: Do NOT revoke URL immediately or download will be cancelled!
    setTimeout(() => {
      try {
        if (a.parentNode) document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      } catch {
        // ignore
      }
    }, 60000);
  },
};

