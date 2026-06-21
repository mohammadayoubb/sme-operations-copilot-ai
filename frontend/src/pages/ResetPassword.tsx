import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { authApi } from "../services/api";
import LogoIcon from "../components/LogoIcon";

export default function ResetPassword() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!token) setError("Invalid or missing reset link. Please request a new one.");
  }, [token]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) { setError("Password must be at least 8 characters."); return; }
    if (password !== confirm) { setError("Passwords do not match."); return; }
    setLoading(true);
    try {
      await authApi.resetPassword(token, password);
      setDone(true);
    } catch (err: any) {
      const msg = err?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Reset failed. The link may have expired.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={S.page}>
      <div style={S.blob1} aria-hidden="true" />
      <div style={S.blob2} aria-hidden="true" />
      <div style={S.card}>
        <div style={S.logoRow}><LogoIcon size={44} /></div>
        <h2 style={S.title}>Set new password</h2>

        {done ? (
          <div style={{ textAlign: "center" }}>
            <div style={S.successIcon}>✓</div>
            <p style={S.successText}>Password updated! You can now sign in with your new password.</p>
            <button style={S.btn} onClick={() => navigate("/login")}>Go to sign in</button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={S.form}>
            <div style={S.field}>
              <label style={S.label}>New Password</label>
              <input
                style={S.input}
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                placeholder="At least 8 characters"
                disabled={!token}
              />
            </div>
            <div style={S.field}>
              <label style={S.label}>Confirm Password</label>
              <input
                style={S.input}
                type="password"
                value={confirm}
                onChange={e => setConfirm(e.target.value)}
                required
                placeholder="••••••••"
                disabled={!token}
              />
            </div>
            {error && <p style={S.error}>{error}</p>}
            <button
              style={{ ...S.btn, opacity: loading || !token ? 0.6 : 1 }}
              type="submit"
              disabled={loading || !token}
            >
              {loading ? "Updating…" : "Update password"}
            </button>
          </form>
        )}

        <p style={S.switchRow}>
          <a href="/login" style={S.link}>Back to sign in</a>
        </p>
      </div>
    </div>
  );
}

const S: Record<string, React.CSSProperties> = {
  page: {
    minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
    background: "var(--bg, #060818)", position: "relative", isolation: "isolate", overflow: "hidden",
  },
  blob1: {
    position: "fixed", top: "-18vh", left: "22%", width: "58vh", height: "58vh",
    background: "radial-gradient(circle, rgba(99,102,241,0.14) 0%, transparent 65%)",
    pointerEvents: "none", zIndex: 0,
  },
  blob2: {
    position: "fixed", bottom: "-12vh", right: "6%", width: "52vh", height: "52vh",
    background: "radial-gradient(circle, rgba(168,85,247,0.12) 0%, transparent 65%)",
    pointerEvents: "none", zIndex: 0,
  },
  card: {
    position: "relative", zIndex: 1, width: 380,
    background: "rgba(255,255,255,0.04)", backdropFilter: "blur(20px)",
    WebkitBackdropFilter: "blur(20px)", border: "1px solid rgba(255,255,255,0.09)",
    borderRadius: 16, padding: "36px 32px 28px",
  },
  logoRow: { display: "flex", justifyContent: "center", marginBottom: 16 },
  title: { textAlign: "center", fontSize: 18, fontWeight: 700, color: "rgba(255,255,255,0.9)", marginBottom: 24 },
  form: { display: "flex", flexDirection: "column", gap: 16 },
  field: { display: "flex", flexDirection: "column", gap: 6 },
  label: { fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.52)", textTransform: "uppercase", letterSpacing: "0.5px" },
  input: {
    background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)",
    borderRadius: 8, padding: "10px 14px", color: "rgba(255,255,255,0.9)", fontSize: 14, outline: "none",
  },
  error: {
    color: "#ef4444", fontSize: 13, background: "#ef444415",
    border: "1px solid #ef444430", borderRadius: 6, padding: "8px 12px",
  },
  btn: {
    background: "#6366f1", color: "#fff", border: "none", borderRadius: 8,
    padding: "11px 0", fontSize: 14, fontWeight: 600, cursor: "pointer", marginTop: 4,
  },
  successIcon: {
    fontSize: 40, color: "#34d399", textAlign: "center",
    marginBottom: 12, fontWeight: 700,
  },
  successText: { color: "rgba(255,255,255,0.6)", fontSize: 14, lineHeight: 1.6, textAlign: "center", marginBottom: 20 },
  switchRow: { textAlign: "center", color: "rgba(255,255,255,0.28)", fontSize: 12, marginTop: 18 },
  link: { color: "#818cf8", textDecoration: "none", fontWeight: 500 },
};
