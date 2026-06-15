import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "../services/api";

export default function Register() {
  const navigate = useNavigate();
  const [businessName, setBusinessName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await authApi.register(businessName, username, password);
      localStorage.setItem("soukpilot_token", res.data.access_token);
      localStorage.setItem("soukpilot_username", res.data.username);
      localStorage.setItem("soukpilot_business", businessName);
      navigate("/", { replace: true });
    } catch (err: any) {
      const msg = err?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Registration failed. Try a different username.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={S.page}>
      <div style={S.blob1} aria-hidden="true" />
      <div style={S.blob2} aria-hidden="true" />

      <div style={S.card}>
        <div style={S.logoRow}>
          <img src="/logo.png" height="40" style={{ objectFit: "contain", maxWidth: 200 }} alt="SoukPilot AI" />
        </div>

        <p style={S.subtitle}>Create your business account</p>

        <form onSubmit={handleSubmit} style={S.form}>
          <div style={S.field}>
            <label style={S.label}>Business Name</label>
            <input
              style={S.input}
              type="text"
              value={businessName}
              onChange={(e) => setBusinessName(e.target.value)}
              required
              placeholder="e.g. Souk Beirut"
            />
          </div>

          <div style={S.field}>
            <label style={S.label}>Username</label>
            <input
              style={S.input}
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              placeholder="e.g. beirut_owner"
            />
          </div>

          <div style={S.field}>
            <label style={S.label}>Password</label>
            <input
              style={S.input}
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
            />
          </div>

          {error && <p style={S.error}>{error}</p>}

          <button style={{ ...S.btn, opacity: loading ? 0.6 : 1 }} type="submit" disabled={loading}>
            {loading ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p style={S.switchRow}>
          Already have an account?{" "}
          <a href="/login" style={S.link}>Sign in</a>
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
