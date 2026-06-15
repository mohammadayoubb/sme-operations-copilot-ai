import React, { FormEvent, useEffect, useState } from "react";
import { adminApi, TenantInfo, TenantStats } from "../services/api";
import LogoIcon from "../components/LogoIcon";

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
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <LogoIcon size={42} />
            <span style={{ fontWeight: 800, fontSize: 22, color: "rgba(255,255,255,0.92)", letterSpacing: "0.3px" }}>
              SoukPilot <span style={{ color: "#818cf8" }}>AI</span>
            </span>
          </div>
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

// ── Stats panel ───────────────────────────────────────────────────────────────

function StatsPanel({ businessId }: { businessId: number }) {
  const [stats, setStats] = useState<TenantStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    adminApi.tenantStats(businessId)
      .then((r) => setStats(r.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [businessId]);

  if (loading) return <div style={S.statsLoading}>Loading stats…</div>;
  if (error || !stats) return <div style={S.statsLoading}>Failed to load stats.</div>;

  const orderStatuses = ["pending", "confirmed", "fulfilled", "cancelled", "pending_review"];
  const invoiceStatuses = ["pending", "processed", "failed"];

  function fmt(n: number) { return n.toLocaleString(); }
  function fmtMoney(n: number) {
    return n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  function fmtDate(s: string | null) {
    if (!s) return "—";
    return new Date(s).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  return (
    <div style={S.statsGrid}>
      {/* Orders */}
      <div style={S.statsCard}>
        <div style={S.statsCardTitle}>Orders</div>
        <div style={S.statsBig}>{fmt(stats.orders.total)}</div>
        <div style={S.statsBreakdown}>
          {orderStatuses.filter(s => stats.orders.by_status[s]).map(s => (
            <span key={s} style={S.statsChip}>
              <span style={{ ...S.statsChipDot, background: ORDER_COLORS[s] ?? "#6366f1" }} />
              {s.replace("_", " ")}: {stats.orders.by_status[s]}
            </span>
          ))}
        </div>
        <div style={S.statsFooter}>Last order: {fmtDate(stats.orders.last_at)}</div>
      </div>

      {/* Invoices */}
      <div style={S.statsCard}>
        <div style={S.statsCardTitle}>Invoices</div>
        <div style={S.statsBig}>{fmt(stats.invoices.total)}</div>
        <div style={S.statsBreakdown}>
          {invoiceStatuses.filter(s => stats.invoices.by_status[s]).map(s => (
            <span key={s} style={S.statsChip}>
              <span style={{ ...S.statsChipDot, background: INV_COLORS[s] ?? "#6366f1" }} />
              {s}: {stats.invoices.by_status[s]}
            </span>
          ))}
        </div>
        <div style={S.statsFooter}>Last upload: {fmtDate(stats.invoices.last_at)}</div>
      </div>

      {/* Products */}
      <div style={S.statsCard}>
        <div style={S.statsCardTitle}>Inventory</div>
        <div style={S.statsBig}>{fmt(stats.products.total)}</div>
        <div style={S.statsBreakdown}>
          <span style={S.statsChip}>
            <span style={{ ...S.statsChipDot, background: "#34d399" }} />
            Total products: {stats.products.total}
          </span>
          {stats.products.low_stock > 0 && (
            <span style={{ ...S.statsChip, color: "#fb923c" }}>
              <span style={{ ...S.statsChipDot, background: "#fb923c" }} />
              Low stock: {stats.products.low_stock}
            </span>
          )}
        </div>
        <div style={S.statsFooter}>
          {stats.products.low_stock === 0 ? "All stock levels healthy" : `${stats.products.low_stock} item${stats.products.low_stock !== 1 ? "s" : ""} need restocking`}
        </div>
      </div>

      {/* Revenue */}
      <div style={S.statsCard}>
        <div style={S.statsCardTitle}>Revenue</div>
        <div style={{ ...S.statsBig, color: "#34d399" }}>${fmtMoney(stats.revenue_total)}</div>
        <div style={S.statsBreakdown}>
          <span style={S.statsChip}>
            <span style={{ ...S.statsChipDot, background: "#34d399" }} />
            Total recorded sales
          </span>
        </div>
        <div style={S.statsFooter}>Last activity: {fmtDate(stats.last_activity_at)}</div>
      </div>

      {/* AI Usage */}
      <div style={S.statsCard}>
        <div style={S.statsCardTitle}>AI Usage</div>
        <div style={S.statsBig}>{fmt(stats.ai.insights_generated)}</div>
        <div style={S.statsBreakdown}>
          <span style={S.statsChip}>
            <span style={{ ...S.statsChipDot, background: "#818cf8" }} />
            Insights generated: {stats.ai.insights_generated}
          </span>
          <span style={S.statsChip}>
            <span style={{ ...S.statsChipDot, background: "#a5b4fc" }} />
            Docs indexed: {stats.ai.documents_indexed}
          </span>
        </div>
        <div style={S.statsFooter}>Powered by SoukPilot AI</div>
      </div>

      {/* Users */}
      <div style={S.statsCard}>
        <div style={S.statsCardTitle}>Users</div>
        <div style={S.statsBig}>{fmt(stats.users.total)}</div>
        <div style={S.statsBreakdown}>
          {Object.entries(stats.users.by_role).map(([role, count]) => (
            <span key={role} style={S.statsChip}>
              <span style={{ ...S.statsChipDot, background: "#6366f1" }} />
              {role}: {count}
            </span>
          ))}
        </div>
        <div style={S.statsFooter}>Registered accounts</div>
      </div>
    </div>
  );
}

const ORDER_COLORS: Record<string, string> = {
  pending: "#fb923c",
  confirmed: "#818cf8",
  fulfilled: "#34d399",
  cancelled: "#f87171",
  pending_review: "#fbbf24",
};

const INV_COLORS: Record<string, string> = {
  pending: "#fb923c",
  processed: "#34d399",
  failed: "#f87171",
};

// ── Dashboard ─────────────────────────────────────────────────────────────────

function AdminDashboard({ onLogout }: { onLogout: () => void }) {
  const [tenants, setTenants] = useState<TenantInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
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
                  <React.Fragment key={t.id}>
                    <tr style={S.tr}>
                      <td style={{ ...S.td, color: "rgba(255,255,255,0.28)", fontSize: 11 }}>{t.id}</td>
                      <td style={{ ...S.td, fontWeight: 500 }}>{t.name}</td>
                      <td style={{ ...S.td, color: "#818cf8" }}>{t.owner_username ?? "—"}</td>
                      <td style={{ ...S.td, color: "rgba(255,255,255,0.42)" }}>{formatDate(t.created_at)}</td>
                      <td style={S.tdNum}>{t.user_count}</td>
                      <td style={S.tdNum}>{t.product_count}</td>
                      <td style={S.tdNum}>{t.order_count}</td>
                      <td style={{ ...S.td, textAlign: "right" }}>
                        <span style={{ display: "inline-flex", gap: 6, alignItems: "center", justifyContent: "flex-end" }}>
                          <button
                            style={expandedId === t.id ? S.statsBtn : S.statsBtnInactive}
                            onClick={() => setExpandedId(expandedId === t.id ? null : t.id)}
                          >
                            {expandedId === t.id ? "▲ Stats" : "▼ Stats"}
                          </button>
                          {confirmId === t.id ? (
                            <>
                              <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)" }}>Sure?</span>
                              <button
                                style={S.deleteBtn}
                                onClick={() => handleDelete(t.id)}
                                disabled={deletingId === t.id}
                              >
                                {deletingId === t.id ? "…" : "Yes, delete"}
                              </button>
                              <button style={S.cancelBtn} onClick={() => setConfirmId(null)}>Cancel</button>
                            </>
                          ) : (
                            <button style={S.deleteBtn} onClick={() => setConfirmId(t.id)}>Delete</button>
                          )}
                        </span>
                      </td>
                    </tr>
                    {expandedId === t.id && (
                      <tr>
                        <td colSpan={8} style={{ padding: 0 }}>
                          <StatsPanel businessId={t.id} />
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
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

  // Stats panel
  statsBtn: {
    background: "rgba(99,102,241,0.18)",
    border: "1px solid rgba(99,102,241,0.4)",
    borderRadius: 6,
    color: "#818cf8",
    fontSize: 11,
    fontWeight: 600,
    padding: "4px 10px",
    cursor: "pointer",
    whiteSpace: "nowrap" as const,
  },
  statsBtnInactive: {
    background: "rgba(255,255,255,0.05)",
    border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: 6,
    color: "rgba(255,255,255,0.35)",
    fontSize: 11,
    fontWeight: 600,
    padding: "4px 10px",
    cursor: "pointer",
    whiteSpace: "nowrap" as const,
  },
  statsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: 1,
    background: "rgba(99,102,241,0.08)",
    borderTop: "1px solid rgba(99,102,241,0.15)",
  },
  statsCard: {
    background: "#070920",
    padding: "16px 20px",
  },
  statsCardTitle: {
    fontSize: 10,
    fontWeight: 700,
    color: "rgba(255,255,255,0.3)",
    textTransform: "uppercase" as const,
    letterSpacing: "0.8px",
    marginBottom: 6,
  },
  statsBig: {
    fontSize: 26,
    fontWeight: 700,
    color: "rgba(255,255,255,0.88)",
    letterSpacing: "-0.5px",
    marginBottom: 8,
    fontVariantNumeric: "tabular-nums",
  },
  statsBreakdown: {
    display: "flex",
    flexWrap: "wrap" as const,
    gap: 4,
    marginBottom: 8,
  },
  statsChip: {
    display: "inline-flex",
    alignItems: "center",
    gap: 4,
    background: "rgba(255,255,255,0.05)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 4,
    padding: "2px 7px",
    fontSize: 11,
    color: "rgba(255,255,255,0.55)",
  },
  statsChipDot: {
    width: 5,
    height: 5,
    borderRadius: "50%",
    flexShrink: 0,
    display: "inline-block",
  },
  statsFooter: {
    fontSize: 11,
    color: "rgba(255,255,255,0.22)",
    marginTop: 4,
  },
  statsLoading: {
    padding: "24px 20px",
    color: "rgba(255,255,255,0.3)",
    fontSize: 13,
    background: "#070920",
    borderTop: "1px solid rgba(99,102,241,0.15)",
  },
};
