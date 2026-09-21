"use client";
import { useState, useEffect } from "react";
import { api, QuizQuestion } from "@/lib/api";
import {
  Brain, RefreshCw, Trophy, ChevronRight, AlertCircle,
  BarChart2, Layers, Zap, RotateCcw, CheckCircle, XCircle
} from "lucide-react";
import MasteryDashboard from "./MasteryDashboard";

type QuizState = "idle" | "loading" | "active" | "done" | "error";
type StudyMode = "quiz" | "flashcard";

const DIFFICULTY_COLORS: Record<string, string> = {
  easy:   "#27ae60",
  medium: "#e67e22",
  hard:   "#e74c3c",
};

const TYPE_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  mcq:           { label: "Multiple Choice", color: "#6366f1", bg: "rgba(99,102,241,0.12)" },
  fill_in_blank: { label: "Fill in the Blank", color: "#0ea5e9", bg: "rgba(14,165,233,0.12)" },
  short_answer:  { label: "Short Answer", color: "#10b981", bg: "rgba(16,185,129,0.12)" },
};

function ScoreRing({ score, total }: { score: number; total: number }) {
  const pct = total > 0 ? score / total : 0;
  const r = 52;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - pct);
  const color = pct >= 0.8 ? "#27ae60" : pct >= 0.5 ? "#e67e22" : "#e74c3c";
  return (
    <div style={{ position: "relative", width: 130, height: 130 }}>
      <svg width={130} height={130} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={65} cy={65} r={r} fill="none" stroke="var(--border)" strokeWidth={10} />
        <circle cx={65} cy={65} r={r} fill="none" stroke={color} strokeWidth={10}
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 1s ease" }} />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
        <span style={{ fontSize: 28, fontWeight: 800, color }}>{score}</span>
        <span style={{ fontSize: 13, color: "var(--text-dim)" }}>/{total}</span>
      </div>
    </div>
  );
}

function FlipCard({ question, onResult, onNext }: {
  question: QuizQuestion; onResult: (c: boolean) => void; onNext: () => void;
}) {
  const [flipped, setFlipped] = useState(false);
  const [rated, setRated] = useState<"correct" | "wrong" | null>(null);
  useEffect(() => { setFlipped(false); setRated(null); }, [question]);
  const answer = question.type === "mcq"
    ? (question.options?.[question.correct_index ?? 0] ?? question.explanation)
    : (question.correct_answer ?? question.explanation);
  function rate(correct: boolean) { setRated(correct ? "correct" : "wrong"); onResult(correct); }
  return (
    <div style={{ perspective: "1200px", width: "100%", maxWidth: 620 }}>
      <div onClick={() => !rated && setFlipped(f => !f)} style={{
        position: "relative", width: "100%", height: 300, cursor: rated ? "default" : "pointer",
        transformStyle: "preserve-3d", transform: flipped ? "rotateY(180deg)" : "rotateY(0deg)",
        transition: "transform 0.55s cubic-bezier(0.4,0,0.2,1)",
      }}>
        <div style={{
          position: "absolute", inset: 0, backfaceVisibility: "hidden", borderRadius: 20,
          padding: "32px 36px", display: "flex", flexDirection: "column", justifyContent: "center",
          alignItems: "center", textAlign: "center", background: "var(--bg-panel)",
          border: "1.5px solid var(--border)", boxShadow: "0 8px 32px rgba(0,0,0,0.08)",
        }}>
          <div style={{ marginBottom: 16, display: "flex", gap: 8 }}>
            {question.type && TYPE_LABELS[question.type] && (
              <span style={{ padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 700, background: TYPE_LABELS[question.type].bg, color: TYPE_LABELS[question.type].color }}>
                {TYPE_LABELS[question.type].label}
              </span>
            )}
          </div>
          <p style={{ fontSize: 20, fontWeight: 600, color: "var(--text-primary)", lineHeight: 1.5, margin: 0 }}>{question.question}</p>
          {!flipped && !rated && <div style={{ marginTop: 20, fontSize: 12, color: "var(--text-dim)", display: "flex", alignItems: "center", gap: 6 }}><RotateCcw size={13} /> Click to reveal answer</div>}
        </div>
        <div style={{
          position: "absolute", inset: 0, backfaceVisibility: "hidden", transform: "rotateY(180deg)",
          borderRadius: 20, padding: "28px 36px", display: "flex", flexDirection: "column",
          justifyContent: "center", alignItems: "center", textAlign: "center",
          background: "linear-gradient(135deg,#f0f9ff,#e0f2fe)", border: "1.5px solid #bae6fd",
          boxShadow: "0 8px 32px rgba(14,165,233,0.12)",
        }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#0369a1", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 12 }}>Answer</div>
          <p style={{ fontSize: 18, fontWeight: 700, color: "#0c4a6e", lineHeight: 1.5, margin: 0 }}>{answer}</p>
          {question.explanation && answer !== question.explanation && (
            <p style={{ fontSize: 13, color: "#0369a1", lineHeight: 1.5, marginTop: 12, opacity: 0.8 }}>{question.explanation}</p>
          )}
        </div>
      </div>
      {flipped && !rated && (
        <div className="fade-in" style={{ display: "flex", gap: 12, marginTop: 16, justifyContent: "center" }}>
          <button onClick={() => rate(false)} style={{ flex: 1, maxWidth: 180, padding: "12px 0", borderRadius: 12, border: "1.5px solid #fca5a5", background: "#fff5f5", color: "#e74c3c", fontWeight: 700, fontSize: 14, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
            <XCircle size={16} /> Still Learning
          </button>
          <button onClick={() => rate(true)} style={{ flex: 1, maxWidth: 180, padding: "12px 0", borderRadius: 12, border: "1.5px solid #86efac", background: "#f0fdf4", color: "#27ae60", fontWeight: 700, fontSize: 14, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
            <CheckCircle size={16} /> Got It!
          </button>
        </div>
      )}
      {rated && (
        <div className="fade-in" style={{ display: "flex", justifyContent: "center", marginTop: 16 }}>
          <button onClick={onNext} style={{ padding: "12px 32px", borderRadius: 12, border: "none", background: "linear-gradient(135deg,#6366f1,#8b5cf6)", color: "#fff", fontWeight: 700, fontSize: 14, cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}>
            Next Card <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}

const optionLabels = ["A", "B", "C", "D"];

export default function QuizMode({ notebookId }: { notebookId: string }) {
  const [quizState, setQuizState] = useState<QuizState>("idle");
  const [studyMode, setStudyMode] = useState<StudyMode>("quiz");
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [answered, setAnswered] = useState(false);
  const [score, setScore] = useState(0);
  const [topic, setTopic] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [showDashboard, setShowDashboard] = useState(false);
  const [weakTopics, setWeakTopics] = useState<string[]>([]);
  const [fillAnswer, setFillAnswer] = useState("");
  const [shortAnswer, setShortAnswer] = useState("");
  const [isGrading, setIsGrading] = useState(false);
  const [gradeResult, setGradeResult] = useState<{ isCorrect: boolean; feedback: string } | null>(null);

  const current = questions[currentIdx];
  const qType = current?.type ?? "mcq";
  const progress = questions.length > 0 ? ((currentIdx + (answered ? 1 : 0)) / questions.length) * 100 : 0;

  function resetQ() { setSelectedIdx(null); setAnswered(false); setFillAnswer(""); setShortAnswer(""); setIsGrading(false); setGradeResult(null); }

  async function startQuiz(weakFocus = false) {
    setQuizState("loading"); setCurrentIdx(0); setScore(0); setErrorMsg(""); setShowDashboard(false); resetQ();
    const focusTopics = weakFocus && weakTopics.length > 0 ? weakTopics : undefined;
    try {
      const res = await api.generateQuiz(notebookId, topic, 20, focusTopics);
      if (res.error) { setErrorMsg(res.error); setQuizState("error"); return; }
      if (!res.questions?.length) { setErrorMsg("No questions generated. Upload more content."); setQuizState("error"); return; }
      setQuestions(res.questions); setQuizState("active");
    } catch (err: any) { setErrorMsg(err.message || "Failed to generate quiz."); setQuizState("error"); }
  }

  async function handleMcqAnswer(idx: number) {
    if (answered) return;
    setSelectedIdx(idx); setAnswered(true);
    const ok = idx === current.correct_index;
    if (ok) setScore(s => s + 1);
    else if (current.topic && !weakTopics.includes(current.topic)) setWeakTopics(p => [...p, current.topic!]);
    if (current.topic) { try { await api.recordQuizResult(notebookId, current.topic, ok); } catch {} }
  }

  async function handleFillSubmit() {
    if (answered) return;
    setAnswered(true);
    const ok = fillAnswer.trim().toLowerCase() === (current.correct_answer ?? "").toLowerCase();
    setGradeResult({ isCorrect: ok, feedback: ok ? "Correct!" : `Correct answer: "${current.correct_answer}"` });
    if (ok) setScore(s => s + 1);
    else if (current.topic && !weakTopics.includes(current.topic)) setWeakTopics(p => [...p, current.topic!]);
    if (current.topic) { try { await api.recordQuizResult(notebookId, current.topic, ok); } catch {} }
  }

  async function handleShortSubmit() {
    if (answered || isGrading) return;
    setIsGrading(true);
    try {
      const r = await api.gradeShortAnswer(notebookId, current.question, shortAnswer, current.grading_rubric ?? "");
      setAnswered(true); setGradeResult({ isCorrect: r.is_correct, feedback: r.feedback });
      if (r.is_correct) setScore(s => s + 1);
      else if (current.topic && !weakTopics.includes(current.topic)) setWeakTopics(p => [...p, current.topic!]);
      if (current.topic) await api.recordQuizResult(notebookId, current.topic, r.is_correct);
    } catch { setGradeResult({ isCorrect: false, feedback: "Error grading. Try again." }); }
    finally { setIsGrading(false); }
  }

  function handleFlashResult(ok: boolean) {
    if (ok) setScore(s => s + 1);
    else if (current.topic && !weakTopics.includes(current.topic)) setWeakTopics(p => [...p, current.topic!]);
    if (current.topic) api.recordQuizResult(notebookId, current.topic, ok).catch(() => {});
  }
  function handleFlashNext() { if (currentIdx + 1 >= questions.length) setQuizState("done"); else setCurrentIdx(i => i + 1); }
  function nextQuestion() { if (currentIdx + 1 >= questions.length) setQuizState("done"); else { setCurrentIdx(i => i + 1); resetQ(); } }

  const isAnswerCorrect = answered && (qType === "mcq" ? selectedIdx === current?.correct_index : gradeResult?.isCorrect);
  const cfg = TYPE_LABELS[qType] ?? TYPE_LABELS.mcq;

  if (showDashboard) return (
    <div style={{ height: "100%", overflowY: "auto" }}>
      <div style={{ padding: "16px 24px", display: "flex", alignItems: "center", gap: 12, borderBottom: "1px solid var(--border)" }}>
        <button onClick={() => setShowDashboard(false)} style={{ background: "none", border: "1px solid var(--border)", borderRadius: 8, padding: "6px 14px", cursor: "pointer", fontSize: 13, fontWeight: 600, color: "var(--text-secondary)" }}>
          ← Back to Quiz
        </button>
        <span style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>Mastery Dashboard</span>
      </div>
      <MasteryDashboard notebookId={notebookId} />
    </div>
  );

  if (quizState === "idle") return (
    <div style={{ height: "100%", overflowY: "auto", padding: "32px 24px", display: "flex", flexDirection: "column", alignItems: "center" }}>
      <div style={{ width: "100%", maxWidth: 640 }}>
        <div style={{ textAlign: "center", marginBottom: 36 }}>
          <div style={{ width: 72, height: 72, borderRadius: 20, margin: "0 auto 16px", background: "linear-gradient(135deg,#6366f1,#8b5cf6)", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 8px 32px rgba(99,102,241,0.4)" }}>
            <Brain size={34} color="#fff" />
          </div>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: "var(--text-primary)", margin: 0 }}>Study Mode</h1>
          <p style={{ fontSize: 14, color: "var(--text-dim)", marginTop: 6 }}>AI-powered quizzes & flashcards from your documents</p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 28 }}>
          {([
            { mode: "quiz" as StudyMode, icon: <Zap size={22} />, title: "Practice Quiz", desc: "MCQ, fill-in-blank & short answer with AI grading" },
            { mode: "flashcard" as StudyMode, icon: <Layers size={22} />, title: "Flashcards", desc: "Flip cards & rate your recall. Great for memorisation" },
          ] as const).map(({ mode, icon, title, desc }) => (
            <button key={mode} onClick={() => setStudyMode(mode)} style={{
              padding: "20px", borderRadius: 16, textAlign: "left", cursor: "pointer",
              border: studyMode === mode ? "2px solid #6366f1" : "1.5px solid var(--border)",
              background: studyMode === mode ? "rgba(99,102,241,0.06)" : "var(--bg-panel)",
              boxShadow: studyMode === mode ? "0 4px 20px rgba(99,102,241,0.15)" : "none",
              transition: "all 0.2s",
            }}>
              <div style={{ color: studyMode === mode ? "#6366f1" : "var(--text-dim)", marginBottom: 10 }}>{icon}</div>
              <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", marginBottom: 4 }}>{title}</div>
              <div style={{ fontSize: 12, color: "var(--text-dim)", lineHeight: 1.5 }}>{desc}</div>
            </button>
          ))}
        </div>

        <div style={{ marginBottom: 20 }}>
          <label style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 8 }}>Focus Topic (optional)</label>
          <input value={topic} onChange={e => setTopic(e.target.value)} onKeyDown={e => e.key === "Enter" && startQuiz()}
            placeholder="e.g. Chapter 3, photosynthesis, market equilibrium..."
            style={{ width: "100%", padding: "12px 16px", borderRadius: 10, border: "1.5px solid var(--border)", fontSize: 14, background: "var(--bg-panel)", color: "var(--text-primary)", outline: "none", boxSizing: "border-box" }} />
        </div>

        {studyMode === "quiz" && (
          <div style={{ display: "flex", gap: 8, marginBottom: 24, flexWrap: "wrap" }}>
            {Object.entries(TYPE_LABELS).map(([t, c]) => (
              <span key={t} style={{ padding: "4px 12px", borderRadius: 20, fontSize: 12, fontWeight: 600, background: c.bg, color: c.color, border: `1px solid ${c.color}30` }}>{c.label}</span>
            ))}
            <span style={{ padding: "4px 12px", borderRadius: 20, fontSize: 12, fontWeight: 600, background: "rgba(16,185,129,0.1)", color: "#10b981", border: "1px solid rgba(16,185,129,0.2)" }}>🤖 AI Graded</span>
          </div>
        )}

        <button onClick={() => startQuiz()} style={{ width: "100%", padding: "15px", borderRadius: 14, border: "none", background: "linear-gradient(135deg,#6366f1,#8b5cf6)", color: "#fff", fontSize: 16, fontWeight: 700, cursor: "pointer", boxShadow: "0 4px 20px rgba(99,102,241,0.35)", display: "flex", alignItems: "center", justifyContent: "center", gap: 10, marginBottom: 14 }}>
          {studyMode === "quiz" ? <Zap size={18} /> : <Layers size={18} />} Start {studyMode === "quiz" ? "Quiz" : "Flashcards"}
        </button>

        {weakTopics.length > 0 && (
          <button onClick={() => startQuiz(true)} style={{ width: "100%", padding: "13px", borderRadius: 14, border: "1.5px solid #e74c3c", background: "rgba(231,76,60,0.06)", color: "#e74c3c", fontSize: 14, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8, marginBottom: 14 }}>
            🎯 Focus on Weak Topics ({weakTopics.length})
          </button>
        )}

        <button onClick={() => setShowDashboard(true)} style={{ width: "100%", padding: "12px", borderRadius: 12, border: "1px solid var(--border)", background: "var(--bg-panel)", color: "var(--text-secondary)", fontSize: 14, fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
          <BarChart2 size={15} /> View Mastery Dashboard
        </button>
      </div>
    </div>
  );

  if (quizState === "loading") return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 20 }}>
      <div style={{ width: 56, height: 56, borderRadius: 16, background: "linear-gradient(135deg,#6366f1,#8b5cf6)", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 4px 20px rgba(99,102,241,0.3)" }}>
        <Brain size={26} color="#fff" />
      </div>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", marginBottom: 4 }}>Generating {studyMode === "quiz" ? "Quiz" : "Flashcards"}…</div>
        <div style={{ fontSize: 13, color: "var(--text-dim)" }}>AI is crafting personalized questions from your documents</div>
      </div>
    </div>
  );

  if (quizState === "error") return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16, padding: 32 }}>
      <AlertCircle size={40} color="#e74c3c" />
      <div style={{ textAlign: "center", maxWidth: 400 }}>
        <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", marginBottom: 8 }}>Generation Failed</div>
        <div style={{ fontSize: 13, color: "var(--text-dim)", lineHeight: 1.6 }}>{errorMsg}</div>
      </div>
      <button onClick={() => setQuizState("idle")} style={{ padding: "10px 24px", borderRadius: 10, background: "#6366f1", color: "#fff", border: "none", fontWeight: 700, cursor: "pointer" }}>Try Again</button>
    </div>
  );

  if (quizState === "done") {
    const pct = questions.length > 0 ? score / questions.length : 0;
    return (
      <div style={{ height: "100%", overflowY: "auto", display: "flex", alignItems: "center", justifyContent: "center", padding: 32 }}>
        <div className="fade-in" style={{ textAlign: "center", maxWidth: 480, width: "100%" }}>
          <Trophy size={48} color="#f59e0b" style={{ marginBottom: 16 }} />
          <h2 style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)", margin: "0 0 4px" }}>{studyMode === "quiz" ? "Quiz Complete!" : "Flashcards Done!"}</h2>
          <p style={{ color: "var(--text-dim)", margin: "0 0 28px", fontSize: 14 }}>{pct >= 0.8 ? "Excellent! 🚀" : pct >= 0.5 ? "Good effort! 💪" : "Keep practicing! 📚"}</p>
          <div style={{ display: "flex", justifyContent: "center", marginBottom: 32 }}><ScoreRing score={score} total={questions.length} /></div>
          {weakTopics.length > 0 && (
            <div style={{ padding: "14px 16px", borderRadius: 12, background: "rgba(231,76,60,0.06)", border: "1px solid rgba(231,76,60,0.2)", marginBottom: 24, textAlign: "left" }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#e74c3c", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>Topics to Review</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {weakTopics.map(t => <span key={t} style={{ padding: "3px 10px", borderRadius: 20, fontSize: 12, fontWeight: 600, background: "rgba(231,76,60,0.1)", color: "#e74c3c", border: "1px solid rgba(231,76,60,0.2)" }}>{t}</span>)}
              </div>
            </div>
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <button onClick={() => startQuiz()} style={{ padding: "13px", borderRadius: 12, border: "none", background: "linear-gradient(135deg,#6366f1,#8b5cf6)", color: "#fff", fontWeight: 700, fontSize: 14, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
              <RefreshCw size={15} /> Try Again
            </button>
            {weakTopics.length > 0 && <button onClick={() => startQuiz(true)} style={{ padding: "13px", borderRadius: 12, border: "1.5px solid #e74c3c", background: "rgba(231,76,60,0.06)", color: "#e74c3c", fontWeight: 700, fontSize: 14, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>🎯 Focus on Weak Topics</button>}
            <button onClick={() => setShowDashboard(true)} style={{ padding: "13px", borderRadius: 12, border: "1px solid var(--border)", background: "var(--bg-panel)", color: "var(--text-secondary)", fontWeight: 600, fontSize: 14, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
              <BarChart2 size={15} /> View Mastery Dashboard
            </button>
            <button onClick={() => setQuizState("idle")} style={{ padding: "10px", borderRadius: 12, border: "1px solid var(--border)", background: "transparent", color: "var(--text-dim)", fontWeight: 600, fontSize: 13, cursor: "pointer" }}>Back to Setup</button>
          </div>
        </div>
      </div>
    );
  }

  if (quizState === "active" && studyMode === "flashcard") return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <div style={{ height: 4, background: "var(--border)" }}>
        <div style={{ height: "100%", width: `${progress}%`, background: "linear-gradient(90deg,#6366f1,#8b5cf6)", transition: "width 0.4s ease" }} />
      </div>
      <div style={{ padding: "12px 20px", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid var(--border)" }}>
        <button onClick={() => setQuizState("idle")} style={{ background: "none", border: "none", color: "var(--text-dim)", cursor: "pointer", fontSize: 13 }}>← Exit</button>
        <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)" }}>Card {currentIdx + 1} of {questions.length}</span>
        <span style={{ fontSize: 13, fontWeight: 700, color: "#27ae60" }}>{score} ✓</span>
      </div>
      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "24px 20px" }}>
        <FlipCard question={current} onResult={handleFlashResult} onNext={handleFlashNext} />
      </div>
    </div>
  );

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <div style={{ height: 4, background: "var(--border)" }}>
        <div style={{ height: "100%", width: `${progress}%`, background: "linear-gradient(90deg,#6366f1,#8b5cf6)", transition: "width 0.4s ease" }} />
      </div>
      <div style={{ padding: "12px 20px", display: "flex", alignItems: "center", gap: 12, borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
        <button onClick={() => setQuizState("idle")} style={{ background: "none", border: "none", color: "var(--text-dim)", cursor: "pointer", fontSize: 13 }}>← Exit</button>
        <div style={{ flex: 1, display: "flex", gap: 8, alignItems: "center" }}>
          <span style={{ fontSize: 12, color: "var(--text-dim)", fontWeight: 600 }}>{currentIdx + 1}/{questions.length}</span>
          <span style={{ padding: "2px 10px", borderRadius: 20, fontSize: 11, fontWeight: 700, background: cfg.bg, color: cfg.color }}>{cfg.label}</span>
          {current?.difficulty && <span style={{ padding: "2px 10px", borderRadius: 20, fontSize: 11, fontWeight: 700, background: `${DIFFICULTY_COLORS[current.difficulty]}18`, color: DIFFICULTY_COLORS[current.difficulty] }}>{current.difficulty}</span>}
          {qType === "short_answer" && <span style={{ padding: "2px 10px", borderRadius: 20, fontSize: 11, fontWeight: 700, background: "rgba(16,185,129,0.1)", color: "#10b981" }}>🤖 AI Graded</span>}
        </div>
        <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>{score}/{currentIdx + (answered ? 1 : 0)}</span>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "24px 20px" }}>
        <div style={{ maxWidth: 640, margin: "0 auto", display: "flex", flexDirection: "column", gap: 18 }}>
          {current?.topic && <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Topic: {current.topic}</span>}

          <div style={{ padding: "22px 24px", borderRadius: 16, background: "var(--bg-panel)", border: "1.5px solid var(--border)", fontSize: 17, fontWeight: 600, color: "var(--text-primary)", lineHeight: 1.6 }}>
            {current?.question}
          </div>

          {(qType === "mcq" || !current?.type) && current?.options?.map((opt, idx) => {
            const isSel = selectedIdx === idx;
            const isOk = answered && idx === current.correct_index;
            const isBad = answered && isSel && idx !== current.correct_index;
            return (
              <button key={idx} onClick={() => handleMcqAnswer(idx)} disabled={answered} style={{
                width: "100%", padding: "14px 18px", borderRadius: 12, textAlign: "left",
                border: isOk ? "2px solid #27ae60" : isBad ? "2px solid #e74c3c" : isSel ? "2px solid #6366f1" : "1.5px solid var(--border)",
                background: isOk ? "#f0fdf4" : isBad ? "#fff5f5" : isSel ? "rgba(99,102,241,0.06)" : "var(--bg-panel)",
                cursor: answered ? "default" : "pointer", transition: "all 0.18s", display: "flex", alignItems: "flex-start", gap: 12,
              }}>
                <span style={{ flexShrink: 0, width: 26, height: 26, borderRadius: 7, background: isOk ? "#27ae60" : isBad ? "#e74c3c" : "var(--border)", color: (isOk || isBad) ? "#fff" : "var(--text-secondary)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700 }}>
                  {isOk ? "✓" : isBad ? "✗" : optionLabels[idx]}
                </span>
                <span style={{ lineHeight: 1.5, fontSize: 14, color: "var(--text-primary)" }}>{opt}</span>
              </button>
            );
          })}

          {qType === "fill_in_blank" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <input type="text" value={fillAnswer} onChange={e => setFillAnswer(e.target.value)} onKeyDown={e => e.key === "Enter" && !answered && handleFillSubmit()}
                placeholder="Type the missing word or phrase..." disabled={answered} autoFocus
                style={{ padding: "14px 16px", borderRadius: 12, border: answered ? (gradeResult?.isCorrect ? "2px solid #27ae60" : "2px solid #e74c3c") : "1.5px solid var(--border)", fontSize: 15, background: "var(--bg-panel)", color: "var(--text-primary)", outline: "none" }} />
              {!answered && <button onClick={handleFillSubmit} disabled={!fillAnswer.trim()} style={{ padding: "13px", borderRadius: 12, border: "none", background: fillAnswer.trim() ? "linear-gradient(135deg,#6366f1,#8b5cf6)" : "var(--border)", color: "#fff", fontWeight: 700, fontSize: 14, cursor: fillAnswer.trim() ? "pointer" : "not-allowed" }}>Submit Answer</button>}
            </div>
          )}

          {qType === "short_answer" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <textarea value={shortAnswer} onChange={e => setShortAnswer(e.target.value)} placeholder="Write your answer in 1-2 sentences..." disabled={answered || isGrading} rows={4} autoFocus
                style={{ padding: "14px 16px", borderRadius: 12, border: answered ? (gradeResult?.isCorrect ? "2px solid #27ae60" : "2px solid #e74c3c") : "1.5px solid var(--border)", fontSize: 15, background: "var(--bg-panel)", color: "var(--text-primary)", outline: "none", fontFamily: "inherit", resize: "vertical" }} />
              {!answered && (
                <button onClick={handleShortSubmit} disabled={!shortAnswer.trim() || isGrading} style={{ padding: "13px", borderRadius: 12, border: "none", background: (shortAnswer.trim() && !isGrading) ? "linear-gradient(135deg,#10b981,#059669)" : "var(--border)", color: "#fff", fontWeight: 700, fontSize: 14, cursor: (shortAnswer.trim() && !isGrading) ? "pointer" : "not-allowed", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                  {isGrading ? <><RefreshCw size={15} /> Grading with AI…</> : "🤖 Submit for AI Grading"}
                </button>
              )}
            </div>
          )}

          {answered && (
            <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ padding: "16px 18px", borderRadius: 14, background: isAnswerCorrect ? "#f0fdf4" : "#fff5f5", border: `1.5px solid ${isAnswerCorrect ? "#86efac" : "#fca5a5"}` }}>
                <div style={{ fontSize: 13, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.05em", color: isAnswerCorrect ? "#166534" : "#991b1b", marginBottom: 8 }}>
                  {isAnswerCorrect ? "✅ Correct!" : "❌ Incorrect"}
                </div>
                {gradeResult?.feedback && qType !== "mcq" && (
                  <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", lineHeight: 1.6, marginBottom: 10, padding: "10px 14px", borderRadius: 8, background: "rgba(0,0,0,0.03)", border: "1px solid var(--border)" }}>
                    💬 {gradeResult.feedback}
                  </div>
                )}
                <div style={{ fontSize: 13, color: "var(--text-dim)", lineHeight: 1.7 }}><strong>Explanation:</strong> {current?.explanation}</div>
              </div>
              <button onClick={nextQuestion} style={{ padding: "13px", borderRadius: 12, border: "none", background: "linear-gradient(135deg,#6366f1,#8b5cf6)", color: "#fff", fontWeight: 700, fontSize: 14, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                {currentIdx + 1 >= questions.length ? <><Trophy size={15} /> Finish Quiz</> : <>Next Question <ChevronRight size={15} /></>}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
