import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "../services/api";

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await authApi.login(username, password);
      if (res.data.role === "superadmin") {
        localStorage.setItem("soukpilot_admin_token", res.data.access_token);
        navigate("/superadmin", { replace: true });
      } else {
        localStorage.setItem("soukpilot_token", res.data.access_token);
        localStorage.setItem("soukpilot_username", res.data.username);
        navigate("/", { replace: true });
      }
    } catch {
      setError("Invalid username or password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={S.page}>
      <div style={S.blob1} aria-hidden="true" />
      <div style={S.blob2} aria-hidden="true" />

      <div style={S.card}>
        {/* Logo */}
        <div style={S.logoRow}>
          <svg width="130" height="32" viewBox="0 0 162 40" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M4 36 L4 19 Q4 4 18 4 Q32 4 32 19 L32 36" stroke="#818cf8" strokeWidth="2" strokeLinecap="round" fill="none"/>
            <path d="M9 36 L9 20 Q9 10 18 10 Q27 10 27 20 L27 36" stroke="#a5b4fc" strokeWidth="1" strokeLinecap="round" fill="none" opacity="0.4"/>
            <line x1="1" y1="36" x2="35" y2="36" stroke="#818cf8" strokeWidth="2" strokeLinecap="round"/>
            <text x="46" y="18" fontFamily="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" fontSize="11" fontWeight="300" fill="rgba(255,255,255,0.28)" letterSpacing="2.5">SOUK</text>
            <text x="46" y="34" fontFamily="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" fontSize="13" fontWeight="800" fill="rgba(255,255,255,0.92)" letterSpacing="2.5">PILOT</text>
            <text x="126" y="34" fontFamily="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" fontSize="9" fontWeight="700" fill="#818cf8" letterSpacing="1">AI</text>
          </svg>
        </div>

        <p style={S.subtitle}>Sign in to your operations dashboard</p>

        <form onSubmit={handleSubmit} style={S.form}>
          <div style={S.field}>
            <label style={S.label}>Username</label>
            <input
              style={S.input}
              type="text"
              autoComplete="off"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              placeholder="Username"
            />
          </div>

          <div style={S.field}>
            <label style={S.label}>Password</label>
            <input
              style={S.input}
              type="password"
              autoComplete="off"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
            />
          </div>

          {error && <p style={S.error}>{error}</p>}

          <button style={{ ...S.btn, opacity: loading ? 0.6 : 1 }} type="submit" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p style={S.switchRow}>
          New business?{" "}
          <a href="/register" style={S.link}>Create an account</a>
        </p>
      </div>
    </div>
  );
}

const S: Record<string, React.CSSProperties> = {
  page: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "var(--bg, #060818)",
    position: "relative",
    isolation: "isolate",
    overflow: "hidden",
  },
  blob1: {
    position: "fixed",
    top: "-18vh",
    left: "22%",
    width: "58vh",
    height: "58vh",
    background: "radial-gradient(circle, rgba(99,102,241,0.14) 0%, transparent 65%)",
    pointerEvents: "none",
    zIndex: 0,
  },
  blob2: {
    position: "fixed",
    bottom: "-12vh",
    right: "6%",
    width: "52vh",
    height: "52vh",
    background: "radial-gradient(circle, rgba(168,85,247,0.12) 0%, transparent 65%)",
    pointerEvents: "none",
    zIndex: 0,
  },
  card: {
    position: "relative",
    zIndex: 1,
    width: 380,
    background: "rgba(255, 255, 255, 0.04)",
    backdropFilter: "blur(20px)",
    WebkitBackdropFilter: "blur(20px)",
    border: "1px solid rgba(255, 255, 255, 0.09)",
    borderRadius: 16,
    padding: "36px 32px 28px",
  },
  logoRow: {
    display: "flex",
    justifyContent: "center",
    marginBottom: 20,
  },
  subtitle: {
    textAlign: "center",
    color: "rgba(255,255,255,0.42)",
    fontSize: 13,
    marginBottom: 28,
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: 16,
  },
  field: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  label: {
    fontSize: 12,
    fontWeight: 600,
    color: "rgba(255,255,255,0.52)",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  input: {
    background: "rgba(255,255,255,0.06)",
    border: "1px solid rgba(255,255,255,0.12)",
    borderRadius: 8,
    padding: "10px 14px",
    color: "rgba(255,255,255,0.9)",
    fontSize: 14,
    outline: "none",
  },
  error: {
    color: "#ef4444",
    fontSize: 13,
    background: "#ef444415",
    border: "1px solid #ef444430",
    borderRadius: 6,
    padding: "8px 12px",
  },
  btn: {
    background: "#6366f1",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    padding: "11px 0",
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
    transition: "background 0.15s",
    marginTop: 4,
  },
  switchRow: {
    textAlign: "center",
    color: "rgba(255,255,255,0.28)",
    fontSize: 12,
    marginTop: 18,
  },
  link: {
    color: "#818cf8",
    textDecoration: "none",
    fontWeight: 500,
  },
};
