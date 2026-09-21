"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Brain, AlertCircle, Target, TrendingUp } from "lucide-react";
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  ResponsiveContainer, Tooltip, Cell
} from "recharts";

interface MasteryStat {
  topic: string;
  total_attempts: number;
  correct_attempts: number;
  mastery_percentage: number;
}

const getMasteryColor = (pct: number) =>
  pct >= 80 ? "#27ae60" : pct >= 60 ? "#e67e22" : "#e74c3c";

export default function MasteryDashboard({ notebookId }: { notebookId: string }) {
  const [stats, setStats] = useState<MasteryStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getQuizMastery(notebookId)
      .then(d => { setStats(d.stats || []); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [notebookId]);

  if (loading) return (
    <div style={{ padding: 40, textAlign: "center", color: "var(--text-dim)", display: "flex", alignItems: "center", justifyContent: "center", gap: 10, height: 200 }}>
      <span className="spinner" /> Loading mastery data…
    </div>
  );

  if (error) return (
    <div style={{ padding: 20, color: "#e74c3c", display: "flex", gap: 8, alignItems: "center" }}>
      <AlertCircle size={16} /> {error}
    </div>
  );

  if (stats.length === 0) return (
    <div style={{ padding: 48, textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
      <div style={{ width: 72, height: 72, borderRadius: "50%", background: "linear-gradient(135deg, rgba(99,102,241,0.1), rgba(139,92,246,0.1))", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Brain size={32} color="#6366f1" />
      </div>
      <div>
        <h3 style={{ margin: 0, color: "var(--text-primary)", fontSize: 18, fontWeight: 700 }}>No Mastery Data Yet</h3>
        <p style={{ margin: "8px 0 0", color: "var(--text-dim)", fontSize: 14, lineHeight: 1.6 }}>
          Take some quizzes to start building your<br />knowledge mastery map!
        </p>
      </div>
    </div>
  );

  const chartData = stats.slice(0, 8).map(s => ({
    subject: s.topic.length > 14 ? s.topic.slice(0, 13) + "…" : s.topic,
    fullTopic: s.topic,
    A: Math.round(s.mastery_percentage),
    fullMark: 100,
  }));

  const barData = stats.map(s => ({
    topic: s.topic.length > 16 ? s.topic.slice(0, 15) + "…" : s.topic,
    mastery: Math.round(s.mastery_percentage),
    attempts: s.total_attempts,
  }));

  const weakTopics = stats.filter(s => s.mastery_percentage < 60);
  const strongTopics = stats.filter(s => s.mastery_percentage >= 80);
  const avgMastery = stats.length > 0 ? Math.round(stats.reduce((a, s) => a + s.mastery_percentage, 0) / stats.length) : 0;

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    const d = payload[0];
    return (
      <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border)", borderRadius: 10, padding: "10px 14px", boxShadow: "0 4px 20px rgba(0,0,0,0.1)" }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 4 }}>{d.payload.fullTopic || d.payload.topic}</div>
        <div style={{ fontSize: 16, fontWeight: 800, color: getMasteryColor(d.value) }}>{d.value}%</div>
        {d.payload.attempts && <div style={{ fontSize: 11, color: "var(--text-dim)", marginTop: 2 }}>{d.payload.attempts} attempts</div>}
      </div>
    );
  };

  return (
    <div style={{ padding: "24px", display: "flex", flexDirection: "column", gap: 24 }}>

      {/* Header */}
      <div>
        <h2 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: "var(--text-primary)" }}>Knowledge Mastery</h2>
        <p style={{ margin: "4px 0 0", color: "var(--text-dim)", fontSize: 14 }}>
          Your performance across topics from generated quizzes
        </p>
      </div>

      {/* Summary Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
        {[
          { label: "Topics Tracked", value: stats.length, icon: <Target size={18} />, color: "#6366f1" },
          { label: "Avg Mastery", value: `${avgMastery}%`, icon: <TrendingUp size={18} />, color: getMasteryColor(avgMastery) },
          { label: "Strong Topics", value: strongTopics.length, icon: <Brain size={18} />, color: "#27ae60" },
        ].map(({ label, value, icon, color }) => (
          <div key={label} style={{ padding: "16px", borderRadius: 14, background: "var(--bg-panel)", border: "1px solid var(--border)", textAlign: "center" }}>
            <div style={{ color, marginBottom: 6, display: "flex", justifyContent: "center" }}>{icon}</div>
            <div style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)" }}>{value}</div>
            <div style={{ fontSize: 11, color: "var(--text-dim)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em", marginTop: 2 }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 20 }}>

        {/* Spider / Radar Chart */}
        <div style={{ flex: "1 1 340px", background: "var(--bg-panel)", borderRadius: 16, padding: "20px", border: "1px solid var(--border)", minHeight: 320 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 16, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            🕸️ Mastery Spider Chart
          </div>
          {chartData.length >= 3 ? (
            <ResponsiveContainer width="100%" height={260}>
              <RadarChart cx="50%" cy="50%" outerRadius="75%" data={chartData}>
                <PolarGrid stroke="var(--border)" strokeDasharray="3 3" />
                <PolarAngleAxis
                  dataKey="subject"
                  tick={{ fill: "var(--text-secondary)", fontSize: 11, fontWeight: 600 }}
                />
                <PolarRadiusAxis
                  angle={90} domain={[0, 100]} tick={false} axisLine={false}
                  tickCount={5}
                />
                <Tooltip content={<CustomTooltip />} />
                <Radar
                  name="Mastery"
                  dataKey="A"
                  stroke="#6366f1"
                  fill="#6366f1"
                  fillOpacity={0.25}
                  strokeWidth={2}
                  dot={{ fill: "#6366f1", r: 4, strokeWidth: 0 }}
                />
              </RadarChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 220, color: "var(--text-dim)", fontSize: 13, textAlign: "center", gap: 8 }}>
              <span style={{ fontSize: 32 }}>🕸️</span>
              Take quizzes on <strong style={{ color: "var(--text-primary)" }}>3+ topics</strong> to unlock the<br />full spider chart!
            </div>
          )}
        </div>

        {/* Bar Chart */}
        <div style={{ flex: "1 1 340px", background: "var(--bg-panel)", borderRadius: 16, padding: "20px", border: "1px solid var(--border)", minHeight: 320 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 16, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            📊 Topic Breakdown
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={barData} margin={{ top: 5, right: 10, left: -20, bottom: 30 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="topic" tick={{ fill: "var(--text-dim)", fontSize: 10 }}
                axisLine={false} tickLine={false} angle={-35} textAnchor="end"
              />
              <YAxis domain={[0, 100]} tick={{ fill: "var(--text-dim)", fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(99,102,241,0.05)" }} />
              <Bar dataKey="mastery" name="Mastery %" radius={[6, 6, 0, 0]} maxBarSize={48}>
                {barData.map((entry, i) => (
                  <Cell key={i} fill={getMasteryColor(entry.mastery)} fillOpacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Weak / Strong panels */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div style={{ background: "var(--bg-panel)", borderRadius: 14, padding: "18px 20px", border: "1px solid var(--border)" }}>
          <h4 style={{ margin: "0 0 12px", color: "#e74c3c", fontSize: 13, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", display: "flex", alignItems: "center", gap: 6 }}>
            🔴 Needs Review (under 60%)
          </h4>
          {weakTopics.length > 0 ? (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {weakTopics.map(t => (
                <span key={t.topic} style={{ background: "#fff5f5", color: "#e74c3c", padding: "4px 12px", borderRadius: 20, fontSize: 13, border: "1px solid #fca5a5", fontWeight: 600 }}>
                  {t.topic} · {Math.round(t.mastery_percentage)}%
                </span>
              ))}
            </div>
          ) : (
            <span style={{ color: "var(--text-dim)", fontSize: 13 }}>No weak topics yet. Great job! 🎉</span>
          )}
        </div>

        <div style={{ background: "var(--bg-panel)", borderRadius: 14, padding: "18px 20px", border: "1px solid var(--border)" }}>
          <h4 style={{ margin: "0 0 12px", color: "#27ae60", fontSize: 13, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", display: "flex", alignItems: "center", gap: 6 }}>
            🟢 Mastered (over 80%)
          </h4>
          {strongTopics.length > 0 ? (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {strongTopics.map(t => (
                <span key={t.topic} style={{ background: "#f0fdf4", color: "#27ae60", padding: "4px 12px", borderRadius: 20, fontSize: 13, border: "1px solid #86efac", fontWeight: 600 }}>
                  {t.topic} · {Math.round(t.mastery_percentage)}%
                </span>
              ))}
            </div>
          ) : (
            <span style={{ color: "var(--text-dim)", fontSize: 13 }}>Keep answering correctly to build strong topics!</span>
          )}
        </div>
      </div>
    </div>
  );
}
