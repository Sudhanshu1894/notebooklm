"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Citation } from "@/lib/api";
import { useState } from "react";

interface TeachingMessageProps {
  content: string;
  citations?: Citation[];
  onCitationClick?: (citation: Citation | null) => void;
  activeCitationNum?: number | null;
}

// Section metadata: emoji, heading text → rendered as distinct styled card
const SECTION_META: Record<string, { emoji: string; color: string; bg: string; border: string }> = {
  "📋 Overview":       { emoji: "📋", color: "#1a3a5c", bg: "linear-gradient(135deg,#e8f4fd,#dceefb)", border: "#90caf9" },
  "💡 Real-World Analogy": { emoji: "💡", color: "#5a3e00", bg: "linear-gradient(135deg,#fffbea,#fff3c4)", border: "#ffd54f" },
  "⚙️ How It Works":  { emoji: "⚙️", color: "#1b4332", bg: "linear-gradient(135deg,#e9f5f0,#d1f0e0)", border: "#66bb6a" },
  "🎯 Concrete Example": { emoji: "🎯", color: "#4a1942", bg: "linear-gradient(135deg,#f5e9fb,#ede0f8)", border: "#ce93d8" },
  "✅ Key Takeaways":  { emoji: "✅", color: "#1a2a40", bg: "linear-gradient(135deg,#eef2ff,#e0e7ff)", border: "#7986cb" },
};

// Parses the markdown output of teaching prompts into sections
function parseSections(markdown: string): { heading: string; body: string }[] {
  // Split on ## headings
  const parts = markdown.split(/\n(?=##\s)/);
  const sections: { heading: string; body: string }[] = [];
  for (const part of parts) {
    const lines = part.trim().split("\n");
    const headingLine = lines[0];
    if (headingLine.startsWith("## ")) {
      const heading = headingLine.replace(/^##\s+/, "").trim();
      const body = lines.slice(1).join("\n").trim();
      sections.push({ heading, body });
    } else if (part.trim()) {
      // Content before the first heading (e.g., a local model warning)
      sections.unshift({ heading: "__preamble__", body: part.trim() });
    }
  }
  return sections;
}

// CitationLink used inside teaching card markdown
function CitationLink({
  num,
  citations,
  onCitationClick,
  activeCitationNum,
}: {
  num: number;
  citations: Citation[];
  onCitationClick?: (c: Citation | null) => void;
  activeCitationNum?: number | null;
}) {
  const cit = citations?.find((c) => c.citation_number === num);
  const isActive = activeCitationNum === num;
  return (
    <span
      className={`citation-pill ${isActive ? "active" : ""}`}
      onClick={() => onCitationClick?.(isActive ? null : cit || null)}
      title={cit?.text_preview || ""}
      style={{ cursor: "pointer" }}
    >
      {num}
    </span>
  );
}

export default function TeachingMessage({
  content,
  citations = [],
  onCitationClick,
  activeCitationNum,
}: TeachingMessageProps) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  // Pre-process citation refs into clickable spans via markdown link format
  const preprocessCitations = (text: string) =>
    text.replace(/\[(\d+)\]/g, "[$1](#cite-$1)");

  const sections = parseSections(content);

  const markdownComponents = {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    a: ({ href, children, ...props }: any) => {
      if (href?.startsWith("#cite-")) {
        const num = parseInt(href.replace("#cite-", ""));
        return (
          <CitationLink
            num={num}
            citations={citations}
            onCitationClick={onCitationClick}
            activeCitationNum={activeCitationNum}
          />
        );
      }
      return <a href={href ?? ""} {...props} target="_blank" rel="noreferrer">{children}</a>;
    },
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, width: "100%" }}>
      {sections.map(({ heading, body }, idx) => {
        // Preamble / warning block (e.g., [LOCAL MODEL] notice)
        if (heading === "__preamble__") {
          return (
            <div
              key="preamble"
              style={{
                padding: "10px 14px",
                borderRadius: 10,
                background: "#fff8e1",
                border: "1px solid #ffe082",
                fontSize: 12.5,
                color: "#5a3e00",
                lineHeight: 1.5,
              }}
            >
              <div className="markdown-body" style={{ fontSize: 12.5 }}>
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                  {preprocessCitations(body)}
                </ReactMarkdown>
              </div>
            </div>
          );
        }

        const meta = SECTION_META[heading];
        const isCollapsed = collapsed[heading];

        return (
          <div
            key={idx}
            className="fade-in"
            style={{
              borderRadius: 14,
              border: `1px solid ${meta?.border ?? "var(--border)"}`,
              overflow: "hidden",
              background: meta?.bg ?? "var(--bg-panel)",
              transition: "box-shadow 0.2s",
            }}
          >
            {/* Section header — clickable to collapse */}
            <button
              onClick={() =>
                setCollapsed((prev) => ({ ...prev, [heading]: !prev[heading] }))
              }
              style={{
                width: "100%",
                textAlign: "left",
                padding: "12px 16px",
                background: "transparent",
                border: "none",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 8,
                borderBottom: isCollapsed ? "none" : `1px solid ${meta?.border ?? "var(--border)"}`,
              }}
            >
              <span style={{ fontSize: 16 }}>{meta?.emoji ?? "📌"}</span>
              <span
                style={{
                  fontWeight: 700,
                  fontSize: 13.5,
                  color: meta?.color ?? "var(--text-primary)",
                  flex: 1,
                }}
              >
                {heading}
              </span>
              <span
                style={{
                  fontSize: 11,
                  color: meta?.color ?? "var(--text-dim)",
                  opacity: 0.6,
                  transition: "transform 0.2s",
                  transform: isCollapsed ? "rotate(-90deg)" : "rotate(0deg)",
                }}
              >
                ▾
              </span>
            </button>

            {/* Section body */}
            {!isCollapsed && (
              <div
                style={{ padding: "12px 16px 16px" }}
                className="markdown-body teaching-body"
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                  {preprocessCitations(body)}
                </ReactMarkdown>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
