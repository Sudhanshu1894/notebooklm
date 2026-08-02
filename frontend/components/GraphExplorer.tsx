"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { api, GraphData } from "@/lib/api";

export default function GraphExplorer({ notebookId }: { notebookId: string }) {
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<GraphData["nodes"][0] | null>(null);
  const [search, setSearch] = useState("");
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    api.getGraph(notebookId)
      .then(setGraph)
      .catch(() => setGraph({ nodes: [], edges: [], demo_mode: true }))
      .finally(() => setLoading(false));
  }, [notebookId]);

  const filteredNodes = graph?.nodes.filter((n) =>
    n.name.toLowerCase().includes(search.toLowerCase()) ||
    n.type.toLowerCase().includes(search.toLowerCase())
  ) ?? [];

  const nodeSet = new Set(filteredNodes.map((n) => n.id));
  const filteredEdges = graph?.edges.filter((e) => nodeSet.has(e.source) && nodeSet.has(e.target)) ?? [];

  // Simple force layout — distribute nodes in a circle
  const W = 700, H = 500, CX = W / 2, CY = H / 2, R = 180;
  const positions: Record<string, { x: number; y: number }> = {};
  filteredNodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / Math.max(filteredNodes.length, 1) - Math.PI / 2;
    positions[node.id] = {
      x: CX + R * Math.cos(angle),
      y: CY + R * Math.sin(angle),
    };
  });

  const TYPE_COLORS: Record<string, string> = {
    PERSON: "#6c63ff", ORG: "#38bdf8", CONCEPT: "#a78bfa",
    PLACE: "#22c55e", EVENT: "#f59e0b", WORK: "#fb7185",
  };

  if (loading) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 12, color: "var(--text-dim)" }}>
        <span className="spinner" /> Loading knowledge graph...
      </div>
    );
  }

  const isEmpty = !graph || (graph.nodes.length === 0);

  return (
    <div style={{ display: "flex", height: "100%", overflow: "hidden" }}>
      {/* Graph canvas */}
      <div style={{ flex: 1, padding: "16px", display: "flex", flexDirection: "column", gap: 12, overflow: "hidden" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.5px" }}>Knowledge Graph</span>
          {graph?.demo_mode && <span className="badge badge-pending">Demo mode — add Neo4j credentials to see live graph</span>}
          {!isEmpty && <span className="badge badge-vector">{graph!.nodes.length} entities · {graph!.edges.length} relations</span>}
          <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Filter entities..." style={{ marginLeft: "auto", width: 200 }} />
        </div>

        {isEmpty ? (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, color: "var(--text-dim)" }}>
            <span style={{ fontSize: 48 }}>⬡</span>
            <p style={{ fontSize: 14, textAlign: "center", maxWidth: 340 }}>
              {graph?.demo_mode
                ? "Add NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD to .env and run scripts/build_graph.py to build the knowledge graph."
                : "No entities found. Index a document and run scripts/build_graph.py first."}
            </p>
          </div>
        ) : (
          <div style={{ flex: 1, border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden", background: "rgba(0,0,0,0.2)" }}>
            <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "100%" }}>
              <defs>
                <radialGradient id="bgGrad" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="rgba(108,99,255,0.04)" />
                  <stop offset="100%" stopColor="rgba(0,0,0,0)" />
                </radialGradient>
                <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(255,255,255,0.15)" />
                </marker>
              </defs>
              <rect width={W} height={H} fill="url(#bgGrad)" />

              {/* Edges */}
              {filteredEdges.map((edge, i) => {
                const from = positions[edge.source];
                const to = positions[edge.target];
                if (!from || !to) return null;
                const mx = (from.x + to.x) / 2;
                const my = (from.y + to.y) / 2;
                return (
                  <g key={i}>
                    <line
                      x1={from.x} y1={from.y} x2={to.x} y2={to.y}
                      stroke="rgba(255,255,255,0.1)" strokeWidth="1.5"
                      markerEnd="url(#arrow)"
                    />
                    <text x={mx} y={my - 4} textAnchor="middle" fill="rgba(255,255,255,0.3)" fontSize="9">
                      {edge.label.replace(/_/g, " ")}
                    </text>
                  </g>
                );
              })}

              {/* Nodes */}
              {filteredNodes.map((node) => {
                const pos = positions[node.id];
                const color = TYPE_COLORS[node.type] || "#888";
                const isSelected = selected?.id === node.id;
                return (
                  <g key={node.id} style={{ cursor: "pointer" }} onClick={() => setSelected(isSelected ? null : node)}>
                    <circle
                      cx={pos.x} cy={pos.y} r={isSelected ? 20 : 14}
                      fill={color} fillOpacity={isSelected ? 1 : 0.7}
                      stroke={isSelected ? "white" : color}
                      strokeWidth={isSelected ? 2 : 1}
                      style={{ filter: isSelected ? `drop-shadow(0 0 8px ${color})` : "none", transition: "all 0.2s" }}
                    />
                    <text x={pos.x} y={pos.y + 28} textAnchor="middle" fill="rgba(255,255,255,0.8)" fontSize="10" fontWeight="500">
                      {node.name.length > 16 ? node.name.substring(0, 14) + "…" : node.name}
                    </text>
                    <text x={pos.x} y={pos.y + 38} textAnchor="middle" fill="rgba(255,255,255,0.3)" fontSize="8">
                      {node.type}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        )}

        {/* Legend */}
        {!isEmpty && (
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {Object.entries(TYPE_COLORS).map(([type, color]) => (
              <div key={type} style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: color }} />
                <span style={{ fontSize: 10, color: "var(--text-dim)" }}>{type}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Right: Entity detail */}
      {selected && (
        <aside style={{ width: 240, borderLeft: "1px solid var(--border)", padding: 16, display: "flex", flexDirection: "column", gap: 12, flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.5px" }}>Entity Detail</span>
            <button style={{ background: "none", border: "none", color: "var(--text-dim)", cursor: "pointer", fontSize: 16 }} onClick={() => setSelected(null)}>✕</button>
          </div>
          <div className="glass-accent" style={{ padding: 14 }}>
            <div style={{ fontWeight: 700, fontSize: "1.1rem", marginBottom: 4 }}>{selected.name}</div>
            <span className="badge" style={{ background: `${TYPE_COLORS[selected.type] || "#888"}22`, color: TYPE_COLORS[selected.type] || "#888", border: `1px solid ${TYPE_COLORS[selected.type] || "#888"}44` }}>
              {selected.type}
            </span>
          </div>
          <div>
            <div style={{ fontSize: 11, color: "var(--text-dim)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.5px" }}>Connected ({filteredEdges.filter(e => e.source === selected.id || e.target === selected.id).length} relations)</div>
            {filteredEdges.filter((e) => e.source === selected.id || e.target === selected.id).map((e, i) => {
              const otherId = e.source === selected.id ? e.target : e.source;
              const other = filteredNodes.find((n) => n.id === otherId);
              return (
                <div key={i} className="glass" style={{ padding: "8px 10px", marginBottom: 6 }}>
                  <div style={{ fontSize: 11, color: "var(--text-dim)" }}>{e.label.replace(/_/g, " ")}</div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>{other?.name || otherId}</div>
                </div>
              );
            })}
          </div>
          {selected.source_chunk_ids?.length > 0 && (
            <div>
              <div style={{ fontSize: 11, color: "var(--text-dim)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.5px" }}>Source Chunks</div>
              {selected.source_chunk_ids.slice(0, 3).map((id) => (
                <div key={id} style={{ fontSize: 10, color: "var(--text-dim)", fontFamily: "monospace", marginBottom: 3 }}>{id}</div>
              ))}
            </div>
          )}
        </aside>
      )}
    </div>
  );
}
