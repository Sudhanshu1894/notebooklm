"use client";
import { useState, useEffect } from "react";
import { supabase } from "@/lib/supabase";
import { useRouter } from "next/navigation";

export default function UpdatePassword() {
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const router = useRouter();

  useEffect(() => {
    // Check if we have an active session (hash in URL is processed by supabase automatically)
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        setError("Invalid or expired password reset link.");
      }
    });
  }, []);

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { error } = await supabase.auth.updateUser({ password });
      if (error) throw error;
      setSuccess(true);
      setTimeout(() => router.push("/"), 2000);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "100vh", background: "var(--bg-base)" }}>
      <div className="glass" style={{ padding: "2.5rem", width: "100%", maxWidth: 400 }}>
        <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "0.5rem", textAlign: "center" }}>Reset Password</h2>
        
        {success ? (
          <div style={{ background: "#ecfdf5", color: "#10b981", padding: "12px", borderRadius: "8px", fontSize: "14px", textAlign: "center" }}>
            Password updated successfully! Redirecting...
          </div>
        ) : (
          <form onSubmit={handleUpdate} style={{ display: "flex", flexDirection: "column", gap: "1rem", marginTop: "1.5rem" }}>
            {error && <div style={{ background: "#fef2f2", color: "#ef4444", padding: "10px", borderRadius: "8px", fontSize: "13px" }}>{error}</div>}
            
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <label style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-secondary)" }}>New Password</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} required placeholder="••••••••" />
            </div>
            
            <button className="btn btn-primary" type="submit" disabled={loading} style={{ marginTop: "0.5rem" }}>
              {loading ? <span className="spinner" style={{ borderColor: "rgba(255,255,255,0.3)", borderTopColor: "white" }} /> : "Update Password"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
