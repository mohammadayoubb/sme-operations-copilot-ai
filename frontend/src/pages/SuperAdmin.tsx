import { FormEvent, useEffect, useState } from "react";
import { adminApi, TenantInfo } from "../services/api";

// ── Login view ────────────────────────────────────────────────────────────────

function AdminLogin({ onSuccess }: { onSuccess: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await adminApi.login(username, password);
      if (res.data.role !== "superadmin") {
        setError("This account does not have superadmin access.");
        return;
      }
      localStorage.setItem("soukpilot_admin_token", res.data.access_token);
      onSuccess();
    } catch {
      setError("Invalid credentials.");
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
          <svg width="130" height="32" viewBox="0 0 162 40" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M4 36 L4 19 Q4 4 18 4 Q32 4 32 19 L32 36" stroke="#818cf8" strokeWidth="2" strokeLinecap="round" fill="none" />
            <path d="M9 36 L9 20 Q9 10 18 10 Q27 10 27 20 L27 36" stroke="#a5b4fc" strokeWidth="1" strokeLinecap="round" fill="none" opacity="0.4" />
            <line x1="1" y1="36" x2="35" y2="36" stroke="#818cf8" strokeWidth="2" strokeLinecap="round" />
            <text x="46" y="18" fontFamily="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" fontSize="11" fontWeight="300" fill="rgba(255,255,255,0.28)" letterSpacing="2.5">SOUK</text>
            <text x="46" y="34" fontFamily="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" fontSize="13" fontWeight="800" fill="rgba(255,255,255,0.92)" letterSpacing="2.5">PILOT</text>
            <text x="126" y="34" fontFamily="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" fontSize="9" fontWeight="700" fill="#818cf8" letterSpacing="1">AI</text>
          </svg>
        </div>
        <p style={S.subtitle}>Super Admin Portal</p>
        <form onSubmit={handleSubmit} style={S.form}>
          <div style={S.field}>
            <label style={S.label}>Username</label>
            <input
              style={S.input}
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              placeholder="superadmin"
            />
          </div>
          <div style={S.field}>
            <label style={S.label}>Password</label>
            <input
              style={S.input}
              type="password"
              autoComplete="current-password"
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
      </div>
    </div>
  );
}

// ── Add Tenant form ────────────────────────────────────────────────────────────

function AddTenantForm({ onCreated }: { onCreated: () => void }) {
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
      await adminApi.createTenant({ business_name: businessName, username, password });
      setBusinessName("");
      setUsername("");
      setPassword("");
      onCreated();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Failed to create tenant.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={S.addForm}>
      <div style={S.addFormFields}>
        <input
          style={{ ...S.input, flex: 1 }}
          placeholder="Business name"
          value={businessName}
          onChange={(e) => setBusinessName(e.target.value)}
          required
        />
        <input
          style={{ ...S.input, flex: 1 }}
          placeholder="Owner username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        <input
          style={{ ...S.input, flex: 1 }}
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button
          style={{ ...S.btn, padding: "10px 20px", whiteSpace: "nowrap", opacity: loading ? 0.6 : 1 }}
          type="submit"
          disabled={loading}
        >
          {loading ? "Creating…" : "Create"}
        </button>
      </div>
      {error && <p style={{ ...S.error, marginTop: 8 }}>{error}</p>}
    </form>
  );
}

// ── Dashboard view ─────────────────────────────────────────────────────────────

function AdminDashboard({ onLogout }: { onLogout: () => void }) {
  const [tenants, setTenants] = useState<TenantInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const res = await adminApi.tenants();
      setTenants(res.data);
    } catch {
      setError("Failed to load tenants. Your session may have expired.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleDelete(id: number) {
    setDeletingId(id);
    setConfirmId(null);
    try {
      await adminApi.deleteTenant(id);
      setTenants((prev) => prev.filter((t) => t.id !== id));
    } catch {
      setError("Failed to delete tenant.");
    } finally {
      setDeletingId(null);
    }
  }

  function formatDate(raw: string | null) {
    if (!raw) return "—";
    return new Date(raw).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  return (
    <div style={S.dashPage}>
      <div style={S.blob1} aria-hidden="true" />
      <div style={S.blob2} aria-hidden="true" />

      <div style={S.dashInner}>
        {/* Header */}
        <div style={S.dashHeader}>
          <div>
            <div style={S.dashTitle}>Tenant Management</div>
            <div style={S.dashSub}>{tenants.length} tenant{tenants.length !== 1 ? "s" : ""} registered</div>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button
              style={{ ...S.btn, padding: "9px 18px", background: showAdd ? "rgba(99,102,241,0.3)" : "#6366f1" }}
              onClick={() => setShowAdd((v) => !v)}
            >
              {showAdd ? "Cancel" : "+ Add Tenant"}
            </button>
            <button style={S.logoutBtn} onClick={onLogout} title="Sign out">
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M6 2H3a1 1 0 00-1 1v10a1 1 0 001 1h3" />
                <path d="M11 11l3-3-3-3" />
                <line x1="14" y1="8" x2="6" y2="8" />
              </svg>
            </button>
          </div>
        </div>

        {/* Add form */}
        {showAdd && (
          <div style={S.addCard}>
            <div style={S.sectionLabel}>New Tenant</div>
            <AddTenantForm onCreated={() => { setShowAdd(false); load(); }} />
          </div>
        )}

        {error && <p style={{ ...S.error, marginBottom: 16 }}>{error}</p>}

        {/* Table */}
        <div style={S.tableCard}>
          {loading ? (
            <div style={S.emptyState}>Loading…</div>
          ) : tenants.length === 0 ? (
            <div style={S.emptyState}>No tenants yet. Add one above.</div>
          ) : (
            <table style={S.table}>
              <thead>
                <tr>
                  {["ID", "Business Name", "Owner", "Created", "Users", "Products", "Orders", ""].map((h) => (
                    <th key={h} style={S.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {tenants.map((t) => (
                  <tr key={t.id} style={S.tr}>
                    <td style={{ ...S.td, color: "rgba(255,255,255,0.28)", fontSize: 11 }}>{t.id}</td>
                    <td style={{ ...S.td, fontWeight: 500 }}>{t.name}</td>
                    <td style={{ ...S.td, color: "#818cf8" }}>{t.owner_username ?? "—"}</td>
                    <td style={{ ...S.td, color: "rgba(255,255,255,0.42)" }}>{formatDate(t.created_at)}</td>
                    <td style={S.tdNum}>{t.user_count}</td>
                    <td style={S.tdNum}>{t.product_count}</td>
                    <td style={S.tdNum}>{t.order_count}</td>
                    <td style={{ ...S.td, textAlign: "right" }}>
                      {confirmId === t.id ? (
                        <span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
                          <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)" }}>Sure?</span>
                          <button
                            style={S.deleteBtn}
                            onClick={() => handleDelete(t.id)}
                            disabled={deletingId === t.id}
                          >
                            {deletingId === t.id ? "…" : "Yes, delete"}
                          </button>
                          <button style={S.cancelBtn} onClick={() => setConfirmId(null)}>Cancel</button>
                        </span>
                      ) : (
                        <button style={S.deleteBtn} onClick={() => setConfirmId(t.id)}>Delete</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Root component ─────────────────────────────────────────────────────────────

export default function SuperAdmin() {
  const [authed, setAuthed] = useState(() => !!localStorage.getItem("soukpilot_admin_token"));

  function handleLogout() {
    localStorage.removeItem("soukpilot_admin_token");
    setAuthed(false);
  }

  if (!authed) return <AdminLogin onSuccess={() => setAuthed(true)} />;
  return <AdminDashboard onLogout={handleLogout} />;
}

// ── Styles ────────────────────────────────────────────────────────────────────

const S: Record<string, React.CSSProperties> = {
  // Shared
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
    background: "rgba(255,255,255,0.04)",
    backdropFilter: "blur(20px)",
    WebkitBackdropFilter: "blur(20px)",
    border: "1px solid rgba(255,255,255,0.09)",
    borderRadius: 16,
    padding: "36px 32px 28px",
  },
  logoRow: { display: "flex", justifyContent: "center", marginBottom: 20 },
  subtitle: { textAlign: "center", color: "rgba(255,255,255,0.42)", fontSize: 13, marginBottom: 28 },
  form: { display: "flex", flexDirection: "column", gap: 16 },
  field: { display: "flex", flexDirection: "column", gap: 6 },
  label: {
    fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.52)",
    textTransform: "uppercase", letterSpacing: "0.5px",
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
    margin: 0,
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
  },

  // Dashboard layout
  dashPage: {
    minHeight: "100vh",
    background: "var(--bg, #060818)",
    position: "relative",
    isolation: "isolate",
    padding: "40px 48px",
  },
  dashInner: {
    position: "relative",
    zIndex: 1,
    maxWidth: 1100,
    margin: "0 auto",
  },
  dashHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 28,
  },
  dashTitle: {
    fontSize: 22,
    fontWeight: 700,
    color: "rgba(255,255,255,0.92)",
    letterSpacing: "-0.3px",
  },
  dashSub: {
    fontSize: 13,
    color: "rgba(255,255,255,0.32)",
    marginTop: 4,
  },
  sectionLabel: {
    fontSize: 11,
    fontWeight: 700,
    color: "rgba(255,255,255,0.3)",
    textTransform: "uppercase",
    letterSpacing: "1px",
    marginBottom: 12,
  },
  addCard: {
    background: "rgba(255,255,255,0.04)",
    border: "1px solid rgba(255,255,255,0.09)",
    borderRadius: 12,
    padding: "20px 24px",
    marginBottom: 20,
  },
  addForm: { display: "flex", flexDirection: "column" },
  addFormFields: { display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" },
  tableCard: {
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 12,
    overflow: "hidden",
  },
  table: { width: "100%", borderCollapse: "collapse" },
  th: {
    fontSize: 10,
    fontWeight: 700,
    color: "rgba(255,255,255,0.25)",
    textTransform: "uppercase",
    letterSpacing: "0.8px",
    padding: "12px 16px",
    textAlign: "left",
    borderBottom: "1px solid rgba(255,255,255,0.06)",
  },
  tr: { borderBottom: "1px solid rgba(255,255,255,0.04)" },
  td: {
    padding: "13px 16px",
    fontSize: 13,
    color: "rgba(255,255,255,0.78)",
    verticalAlign: "middle",
  },
  tdNum: {
    padding: "13px 16px",
    fontSize: 13,
    color: "rgba(255,255,255,0.45)",
    textAlign: "center",
    fontVariantNumeric: "tabular-nums",
  },
  emptyState: {
    padding: "40px 24px",
    textAlign: "center",
    color: "rgba(255,255,255,0.25)",
    fontSize: 13,
  },
  deleteBtn: {
    background: "rgba(239,68,68,0.12)",
    border: "1px solid rgba(239,68,68,0.25)",
    borderRadius: 6,
    color: "#f87171",
    fontSize: 11,
    fontWeight: 600,
    padding: "4px 10px",
    cursor: "pointer",
  },
  cancelBtn: {
    background: "rgba(255,255,255,0.05)",
    border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: 6,
    color: "rgba(255,255,255,0.4)",
    fontSize: 11,
    padding: "4px 10px",
    cursor: "pointer",
  },
  logoutBtn: {
    background: "transparent",
    border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: 6,
    color: "rgba(255,255,255,0.35)",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "7px 9px",
    flexShrink: 0,
  },
};
