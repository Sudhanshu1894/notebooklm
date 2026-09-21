"use client";
import { useState } from "react";
import { supabase } from "@/lib/supabase";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"login" | "signup" | "reset">("login");
  const [msg, setMsg] = useState<string | null>(null);

  async function handleAuth(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMsg(null);
    
    try {
      if (mode === "signup") {
        const { error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        setMsg("Check your email for the confirmation link!");
      } else if (mode === "login") {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      } else if (mode === "reset") {
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: `${window.location.origin}/update-password`,
        });
        if (error) throw error;
        setMsg("Password reset email sent! Check your inbox.");
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
      <div className="glass" style={{ padding: "2.5rem", width: "100%", maxWidth: 400 }}>
        <div style={{ textAlign: "center", marginBottom: "2rem" }}>
          <div style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: 52, height: 52, borderRadius: "14px", background: "linear-gradient(135deg, #6366f1 0%, #a855f7 60%, #ec4899 100%)", marginBottom: "1rem", boxShadow: "0 4px 20px rgba(99,102,241,0.4)" }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill="white"/>
            </svg>
          </div>
          <h2 style={{ fontSize: "1.6rem", fontWeight: 800, letterSpacing: "-0.5px" }}>
            {mode === "reset" ? "Reset Password" : "Welcome to Lumina"}
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem", marginTop: "0.5rem" }}>
            {mode === "reset" ? "Enter your email to receive a reset link" : "Illuminate your knowledge with AI"}
          </p>
        </div>
        
        {error && <div style={{ background: "#fef2f2", color: "#ef4444", padding: "10px", borderRadius: "8px", fontSize: "13px", marginBottom: "1rem" }}>{error}</div>}
        {msg && <div style={{ background: "#ecfdf5", color: "#10b981", padding: "10px", borderRadius: "8px", fontSize: "13px", marginBottom: "1rem" }}>{msg}</div>}

        <form onSubmit={handleAuth} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <label style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-secondary)" }}>Email Address</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required placeholder="you@example.com" />
          </div>
          
          {mode !== "reset" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <label style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-secondary)" }}>Password</label>
                {mode === "login" && (
                  <button type="button" onClick={() => setMode("reset")} style={{ background: "none", border: "none", color: "var(--accent)", fontSize: "12px", cursor: "pointer" }}>
                    Forgot password?
                  </button>
                )}
              </div>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} required placeholder="••••••••" />
            </div>
          )}
          
          <button className="btn btn-primary" type="submit" disabled={loading} style={{ marginTop: "0.5rem" }}>
            {loading ? <span className="spinner" style={{ borderColor: "rgba(255,255,255,0.3)", borderTopColor: "white" }} /> : (mode === "signup" ? "Sign Up" : mode === "reset" ? "Send Reset Email" : "Log In")}
          </button>
        </form>
        
        <div style={{ marginTop: "1.5rem", textAlign: "center", fontSize: "13px", color: "var(--text-secondary)" }}>
          {mode === "reset" ? (
            <button type="button" onClick={() => setMode("login")} style={{ background: "none", border: "none", color: "var(--accent)", fontWeight: 600, cursor: "pointer" }}>Back to Login</button>
          ) : mode === "signup" ? (
            <>Already have an account? <button type="button" onClick={() => setMode("login")} style={{ background: "none", border: "none", color: "var(--accent)", fontWeight: 600, cursor: "pointer" }}>Log in</button></>
          ) : (
            <>Don&apos;t have an account? <button type="button" onClick={() => setMode("signup")} style={{ background: "none", border: "none", color: "var(--accent)", fontWeight: 600, cursor: "pointer" }}>Sign up</button></>
          )}
        </div>
      </div>
    </div>
  );
}
