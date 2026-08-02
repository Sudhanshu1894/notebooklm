// Central API client for GraphRAG backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Notebook {
  notebook_id: string;
  name: string;
  description: string;
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
}

export interface GraphData {
  nodes: { id: string; name: string; type: string; source_chunk_ids: string[] }[];
  edges: { source: string; target: string; label: string; description: string }[];
  demo_mode?: boolean;
}

export const api = {
  async createNotebook(name: string, description = ""): Promise<Notebook> {
    const res = await fetch(`${API_BASE}/notebooks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async listNotebooks(): Promise<Notebook[]> {
    const res = await fetch(`${API_BASE}/notebooks`);
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

  async chat(notebookId: string, query: string, topK = 5): Promise<ChatResponse> {
    const res = await fetch(`${API_BASE}/notebooks/${notebookId}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: topK }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getGraph(notebookId: string): Promise<GraphData> {
    const res = await fetch(`${API_BASE}/notebooks/${notebookId}/graph`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
};
