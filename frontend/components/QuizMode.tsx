"use client";
import { useState } from "react";
import { api, QuizQuestion } from "@/lib/api";
import { Brain, RefreshCw, Trophy, ChevronRight, AlertCircle } from "lucide-react";

type QuizState = "idle" | "loading" | "active" | "done" | "error";

const DIFFICULTY_COLORS: Record<string, string> = {
  easy:   "#27ae60",
  medium: "#e67e22",
  hard:   "#e74c3c",
};

const ENCOURAGEMENTS = [
  "Excellent work! 🚀",
  "You're a quick learner! ⭐",
  "Great effort! Keep going! 💪",
  "Solid understanding! 🎓",
  "Well done! Knowledge is power! 🔥",
];

function ScoreRing({ score, total }: { score: number; total: number }) {
  const pct = total > 0 ? score / total : 0;
  const r = 44;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - pct);
  const color = pct >= 0.8 ? "#27ae60" : pct >= 0.5 ? "#e67e22" : "#e74c3c";

  return (
    <div style={{ position: "relative", width: 110, height: 110 }}>
      <svg width={110} height={110} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={55} cy={55} r={r} fill="none" stroke="#f0ece6" strokeWidth={10} />
        <circle
          cx={55} cy={55} r={r} fill="none"
          stroke={color} strokeWidth={10}
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.8s ease" }}
        />
      </svg>
      <div style={{
        position: "absolute", inset: 0,
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
      }}>
        <span style={{ fontSize: 22, fontWeight: 800, color }}>{score}</span>
        <span style={{ fontSize: 11, color: "var(--text-dim)" }}>/{total}</span>
      </div>
    </div>
  );
}

export default function QuizMode({ notebookId }: { notebookId: string }) {
  const [quizState, setQuizState] = useState<QuizState>("idle");
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [answered, setAnswered] = useState(false);
  const [score, setScore] = useState(0);
  const [topic, setTopic] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const current = questions[currentIdx];
  const progress = questions.length > 0 ? ((currentIdx + (answered ? 1 : 0)) / questions.length) * 100 : 0;

  async function startQuiz() {
    setQuizState("loading");
    setCurrentIdx(0);
    setScore(0);
    setSelectedIdx(null);
    setAnswered(false);
    setErrorMsg("");
    try {
      const res = await api.generateQuiz(notebookId, topic, 20);
      if (res.error) {
        setErrorMsg(res.error);
        setQuizState("error");
        return;
      }
      if (!res.questions || res.questions.length === 0) {
        setErrorMsg("No questions could be generated. Please upload more document content.");
        setQuizState("error");
        return;
      }
      setQuestions(res.questions);
      setQuizState("active");
    } catch (e) {
      setErrorMsg(`Failed to generate quiz: ${e}`);
      setQuizState("error");
    }
  }

  function handleAnswer(optionIdx: number) {
    if (answered) return;
    setSelectedIdx(optionIdx);
    setAnswered(true);
    if (optionIdx === current.correct_index) {
      setScore((s) => s + 1);
    }
  }

  function nextQuestion() {
    if (currentIdx + 1 >= questions.length) {
      setQuizState("done");
    } else {
      setCurrentIdx((i) => i + 1);
      setSelectedIdx(null);
      setAnswered(false);
    }
  }

  function getOptionStyle(idx: number): React.CSSProperties {
    const base: React.CSSProperties = {
      padding: "13px 16px",
      borderRadius: 10,
      border: "2px solid var(--border)",
      background: "var(--bg-panel)",
      cursor: answered ? "default" : "pointer",
      transition: "all 0.18s",
      textAlign: "left",
      fontSize: 14,
      lineHeight: 1.5,
      color: "var(--text-primary)",
      fontFamily: "inherit",
      width: "100%",
    };

    if (!answered) {
      return { ...base, cursor: "pointer" };
    }

    if (idx === current.correct_index) {
      return {
        ...base,
        border: "2px solid #27ae60",
        background: "#f0fdf4",
        color: "#166534",
        fontWeight: 600,
      };
    }
    if (idx === selectedIdx) {
      return {
        ...base,
        border: "2px solid #e74c3c",
        background: "#fff5f5",
        color: "#991b1b",
      };
    }
    return { ...base, opacity: 0.5 };
  }

  const optionLabels = ["A", "B", "C", "D"];
  const encouragement = ENCOURAGEMENTS[Math.floor(Math.random() * ENCOURAGEMENTS.length)];

  // ── Idle / Start screen ───────────────────────────────────────────
  if (quizState === "idle" || quizState === "error") {
    return (
      <div style={{
        height: "100%", display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        padding: 32, gap: 20,
      }}>
        <div style={{
          width: 72, height: 72, borderRadius: 20,
          background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
          display: "flex", alignItems: "center", justifyContent: "center",
          boxShadow: "0 8px 32px rgba(99,102,241,0.3)",
        }}>
          <Brain size={36} color="#fff" />
        </div>

        <div style={{ textAlign: "center" }}>
          <h2 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--text-primary)", marginBottom: 8 }}>
            Test Your Knowledge
          </h2>
          <p style={{ color: "var(--text-dim)", fontSize: 14, lineHeight: 1.6, maxWidth: 380 }}>
            The AI will generate 5 multiple-choice questions from your uploaded documents.
            Focus on a specific topic, or leave blank for a broad quiz.
          </p>
        </div>

        {quizState === "error" && (
          <div style={{
            display: "flex", gap: 8, alignItems: "flex-start",
            padding: "12px 16px", borderRadius: 10,
            background: "#fff5f5", border: "1px solid #fca5a5",
            maxWidth: 420, color: "#991b1b", fontSize: 13, lineHeight: 1.5,
          }}>
            <AlertCircle size={15} style={{ flexShrink: 0, marginTop: 1 }} />
            {errorMsg}
          </div>
        )}

        <div style={{ width: "100%", maxWidth: 400, display: "flex", flexDirection: "column", gap: 10 }}>
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Topic focus (optional, e.g. 'IAM policies')"
            style={{
              padding: "11px 14px", borderRadius: 10,
              border: "1.5px solid var(--border)",
              background: "var(--bg-panel)", color: "var(--text-primary)",
              fontSize: 14, fontFamily: "inherit", outline: "none",
              transition: "border-color 0.18s",
            }}
            onFocus={(e) => (e.target.style.borderColor = "#6366f1")}
            onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
            onKeyDown={(e) => e.key === "Enter" && startQuiz()}
          />
          <button
            onClick={startQuiz}
            style={{
              padding: "13px 24px", borderRadius: 10, border: "none",
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              color: "#fff", fontSize: 15, fontWeight: 700,
              cursor: "pointer", display: "flex", alignItems: "center",
              justifyContent: "center", gap: 8,
              boxShadow: "0 4px 16px rgba(99,102,241,0.35)",
              transition: "transform 0.15s, box-shadow 0.15s",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-1px)";
              (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 6px 20px rgba(99,102,241,0.45)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.transform = "translateY(0)";
              (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 4px 16px rgba(99,102,241,0.35)";
            }}
          >
            <Brain size={17} /> Generate Quiz
          </button>
        </div>
      </div>
    );
  }

  // ── Loading ───────────────────────────────────────────────────────
  if (quizState === "loading") {
    return (
      <div style={{
        height: "100%", display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center", gap: 20,
      }}>
        <div style={{
          width: 56, height: 56, borderRadius: 16,
          background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
          display: "flex", alignItems: "center", justifyContent: "center",
          animation: "pulse 1.5s ease-in-out infinite",
        }}>
          <Brain size={28} color="#fff" />
        </div>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)" }}>
            Generating your quiz…
          </div>
          <div style={{ fontSize: 13, color: "var(--text-dim)", marginTop: 6 }}>
            Reading your documents and crafting questions
          </div>
        </div>
        <div style={{
          display: "flex", gap: 6, alignItems: "center",
        }}>
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              style={{
                width: 8, height: 8, borderRadius: "50%",
                background: "#6366f1",
                animation: `bounce 1.2s ${i * 0.2}s ease-in-out infinite`,
              }}
            />
          ))}
        </div>
      </div>
    );
  }

  // ── Done / Score screen ───────────────────────────────────────────
  if (quizState === "done") {
    const pct = Math.round((score / questions.length) * 100);
    return (
      <div style={{
        height: "100%", display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center", gap: 24, padding: 32,
      }}>
        <div style={{
          display: "flex", flexDirection: "column", alignItems: "center",
          gap: 16, animation: "fadeIn 0.5s ease",
        }}>
          <Trophy size={40} color="#f59e0b" />
          <h2 style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--text-primary)", textAlign: "center" }}>
            Quiz Complete!
          </h2>
        </div>

        <ScoreRing score={score} total={questions.length} />

        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
            {score >= questions.length * 0.8
              ? encouragement
              : score >= questions.length * 0.5
              ? "Good effort! Review the explanations and try again."
              : "Keep studying! Review the material and try again."}
          </div>
          <div style={{ fontSize: 13, color: "var(--text-dim)" }}>
            You scored {score}/{questions.length} ({pct}%)
          </div>
        </div>

        <div style={{ display: "flex", gap: 10 }}>
          <button
            onClick={startQuiz}
            style={{
              padding: "11px 20px", borderRadius: 10, border: "none",
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              color: "#fff", fontSize: 14, fontWeight: 600,
              cursor: "pointer", display: "flex", alignItems: "center", gap: 6,
              boxShadow: "0 4px 12px rgba(99,102,241,0.3)",
            }}
          >
            <RefreshCw size={14} /> Try Again
          </button>
          <button
            onClick={() => { setQuizState("idle"); setQuestions([]); setScore(0); setTopic(""); }}
            style={{
              padding: "11px 20px", borderRadius: 10,
              border: "1.5px solid var(--border)",
              background: "var(--bg-panel)", color: "var(--text-primary)",
              fontSize: 14, fontWeight: 600, cursor: "pointer",
            }}
          >
            New Topic
          </button>
        </div>
      </div>
    );
  }

  // ── Active quiz ───────────────────────────────────────────────────
  return (
    <div style={{
      height: "100%", overflowY: "auto", padding: "24px 20px",
      display: "flex", justifyContent: "center",
    }}>
      <div style={{ width: "100%", maxWidth: 680, display: "flex", flexDirection: "column", gap: 20 }}>

        {/* Progress header */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Question {currentIdx + 1} of {questions.length}
            </span>
            {current.difficulty && (
              <span style={{
                fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 6,
                background: `${DIFFICULTY_COLORS[current.difficulty]}20`,
                color: DIFFICULTY_COLORS[current.difficulty],
                textTransform: "uppercase", letterSpacing: "0.05em",
              }}>
                {current.difficulty}
              </span>
            )}
          </div>
          {/* Progress bar */}
          <div style={{ height: 4, background: "var(--border)", borderRadius: 2, overflow: "hidden" }}>
            <div style={{
              height: "100%", width: `${progress}%`,
              background: "linear-gradient(90deg, #6366f1, #8b5cf6)",
              borderRadius: 2, transition: "width 0.4s ease",
            }} />
          </div>
        </div>

        {/* Question card */}
        <div style={{
          padding: "22px 24px", borderRadius: 16,
          background: "var(--bg-panel)",
          border: "1.5px solid var(--border)",
          boxShadow: "0 4px 20px rgba(0,0,0,0.06)",
        }}>
          <p style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.6, margin: 0 }}>
            {current.question}
          </p>
          {current.source_hint && (
            <div style={{ marginTop: 10, fontSize: 11.5, color: "var(--text-dim)" }}>
              📄 Source: {current.source_hint}
            </div>
          )}
        </div>

        {/* Answer options */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {current.options.map((option, idx) => (
            <button
              key={idx}
              onClick={() => handleAnswer(idx)}
              style={getOptionStyle(idx)}
            >
              <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                <span style={{
                  flexShrink: 0, width: 24, height: 24, borderRadius: 6,
                  background: answered && idx === current.correct_index
                    ? "#27ae60"
                    : answered && idx === selectedIdx
                    ? "#e74c3c"
                    : "var(--border)",
                  color: answered && (idx === current.correct_index || idx === selectedIdx) ? "#fff" : "var(--text-secondary)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 11, fontWeight: 700, transition: "all 0.2s",
                }}>
                  {answered && idx === current.correct_index ? "✓" : answered && idx === selectedIdx ? "✗" : optionLabels[idx]}
                </span>
                <span style={{ lineHeight: 1.5 }}>{option}</span>
              </div>
            </button>
          ))}
        </div>

        {/* Explanation + Next (shown after answering) */}
        {answered && (
          <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{
              padding: "14px 16px", borderRadius: 12,
              background: selectedIdx === current.correct_index ? "#f0fdf4" : "#fff5f5",
              border: `1.5px solid ${selectedIdx === current.correct_index ? "#86efac" : "#fca5a5"}`,
            }}>
              <div style={{
                fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em",
                color: selectedIdx === current.correct_index ? "#166534" : "#991b1b",
                marginBottom: 6,
              }}>
                {selectedIdx === current.correct_index ? "✅ Correct!" : "❌ Incorrect"}
              </div>
              <div style={{ fontSize: 13.5, color: "var(--text-primary)", lineHeight: 1.6 }}>
                {current.explanation}
              </div>
            </div>

            <button
              onClick={nextQuestion}
              style={{
                alignSelf: "flex-end",
                padding: "11px 22px", borderRadius: 10, border: "none",
                background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                color: "#fff", fontSize: 14, fontWeight: 700,
                cursor: "pointer", display: "flex", alignItems: "center", gap: 6,
                boxShadow: "0 4px 12px rgba(99,102,241,0.3)",
                transition: "transform 0.15s",
              }}
            >
              {currentIdx + 1 >= questions.length ? (
                <><Trophy size={15} /> See Results</>
              ) : (
                <>Next Question <ChevronRight size={15} /></>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
