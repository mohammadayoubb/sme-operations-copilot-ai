import { useEffect, useState } from "react";
import PageShell from "../components/PageShell";
import { anomalyApi, forecastApi, invoicesApi, ordersApi, productsApi, reportsApi } from "../services/api";

interface Product { id: number; name: string; current_stock: number | null; reorder_level: number | null; }
interface OrderRow { id: number; status: string; }
interface InvoiceRow { id: number; invoice_date: string | null; invoice_total: number | null; currency: string | null; status: string; }
interface Forecast { product_id: number; product_name: string; current_stock: number; days_until_stockout: number | null; reorder_by_date: string | null; }
interface LatestReport { data_json: { sales: { this_week: number; change_pct: number | null }; profit: { this_week: number; change_pct: number | null } } | null; }
interface AnomalyAlert { product_name: string; anomaly_date: string; direction: string; actual_qty: number; expected_qty: number; pct_deviation: number; explanation: string; }

function ChangeBadge({ pct }: { pct: number | null | undefined }) {
  if (pct == null) return null;
  const up = pct >= 0;
  return (
    <span style={{ color: up ? "var(--success)" : "var(--danger)", fontSize: 11, fontWeight: 600, marginTop: 4, display: "block" }}>
      {up ? "▲" : "▼"} {Math.abs(pct).toFixed(1)}% vs last week
    </span>
  );
}

export default function Dashboard() {
  const [products, setProducts] = useState<Product[]>([]);
  const [orders, setOrders] = useState<OrderRow[]>([]);
  const [invoices, setInvoices] = useState<InvoiceRow[]>([]);
  const [reorders, setReorders] = useState<Forecast[]>([]);
  const [report, setReport] = useState<LatestReport | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [p, o, inv, fc] = await Promise.all([
          productsApi.list(),
          ordersApi.list(),
          invoicesApi.list(),
          forecastApi.reorder(),
        ]);
        setProducts(p.data);
        setOrders(o.data);
        setInvoices(inv.data);
        setReorders(fc.data);

        // Latest report is optional — graceful fallback if none generated yet
        try {
          const r = await reportsApi.latest();
          setReport(r.data);
        } catch {
          /* no report yet — stat cards show "—" */
        }

        // Anomaly alerts — non-blocking, best-effort
        try {
          const a = await anomalyApi.alerts();
          setAnomalies(a.data.alerts ?? []);
        } catch {
          /* anomaly scan failed — panel stays hidden */
        }
      } catch (e: any) {
        setError(e?.response?.data?.detail ?? "Failed to load dashboard data.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const lowStockCount = products.filter(
    (p) => (p.current_stock ?? 0) <= (p.reorder_level ?? 0)
  ).length;

  const pendingCount = orders.filter((o) => o.status === "pending").length;

  const salesData = report?.data_json?.sales ?? null;
  const profitData = report?.data_json?.profit ?? null;

  const STAT_CARDS = [
    {
      label: "Sales (this week)",
      value: salesData != null ? `$${salesData.this_week.toFixed(2)}` : "—",
      color: "#6c63ff",
      badge: <ChangeBadge pct={salesData?.change_pct} />,
    },
    {
      label: "Gross Profit",
      value: profitData != null ? `$${profitData.this_week.toFixed(2)}` : "—",
      color: "#22c55e",
      badge: <ChangeBadge pct={profitData?.change_pct} />,
    },
    {
      label: "Low Stock Alerts",
      value: loading ? "…" : String(lowStockCount),
      color: "#f59e0b",
      badge: null,
    },
    {
      label: "Pending Orders",
      value: loading ? "…" : String(pendingCount),
      color: "#ef4444",
      badge: null,
    },
  ];

  return (
    <PageShell title="Dashboard" subtitle="Your business at a glance">
      {error && <div style={styles.errorBanner}>⚠ {error}</div>}

      <div style={styles.grid}>
        {STAT_CARDS.map((c) => (
          <div key={c.label} style={{ ...styles.card, borderTopColor: c.color }}>
            <p style={styles.cardLabel}>{c.label}</p>
            <p style={{ ...styles.cardValue, color: c.color }}>{c.value}</p>
            {c.badge}
          </div>
        ))}
      </div>

      <div style={styles.row}>
        {/* Recent Invoices */}
        <div style={styles.panel}>
          <h3 style={styles.panelTitle}>Recent Invoices</h3>
          {loading ? (
            <div style={styles.muted}>Loading…</div>
          ) : invoices.length === 0 ? (
            <div style={styles.muted}>No invoices yet. Upload one to get started.</div>
          ) : (
            <table style={styles.table}>
              <thead>
                <tr>
                  {["#", "Date", "Total", "Status"].map((h) => (
                    <th key={h} style={styles.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {invoices.slice(0, 5).map((inv) => (
                  <tr key={inv.id} style={styles.tr}>
                    <td style={styles.td}>{inv.id}</td>
                    <td style={styles.td}>{inv.invoice_date ?? "—"}</td>
                    <td style={styles.td}>{inv.invoice_total != null ? `$${Number(inv.invoice_total).toFixed(2)}` : "—"} {inv.currency ?? ""}</td>
                    <td style={styles.td}>
                      <span style={{
                        ...styles.badge,
                        background: inv.status === "processed" ? "#22c55e22" : inv.status === "failed" ? "#ef444422" : "#6c63ff22",
                        color: inv.status === "processed" ? "#22c55e" : inv.status === "failed" ? "#ef4444" : "#6c63ff",
                      }}>
                        {inv.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Reorder Alerts */}
        <div style={styles.panel}>
          <h3 style={styles.panelTitle}>Reorder Alerts</h3>
          {loading ? (
            <div style={styles.muted}>Loading…</div>
          ) : reorders.length === 0 ? (
            <div style={styles.muted}>No reorder alerts. Stock levels look healthy.</div>
          ) : (
            <div style={styles.alertList}>
              {reorders.slice(0, 5).map((f) => (
                <div key={f.product_id} style={styles.alertRow}>
                  <div>
                    <span style={styles.alertName}>{f.product_name}</span>
                    <span style={styles.alertSub}>
                      {f.days_until_stockout != null
                        ? `Runs out in ${f.days_until_stockout} days`
                        : `Stock: ${f.current_stock}`}
                    </span>
                  </div>
                  <div style={styles.alertMeta}>
                    <span style={styles.reorderBadge}>REORDER</span>
                    {f.reorder_by_date && (
                      <span style={styles.alertDate}>by {f.reorder_by_date}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Anomaly Alerts */}
      {anomalies.length > 0 && (
        <div style={styles.panel}>
          <h3 style={styles.panelTitle}>
            AI Anomaly Alerts
            <span style={styles.anomalyBadge}>{anomalies.length} detected</span>
          </h3>
          <div style={styles.anomalyList}>
            {anomalies.slice(0, 4).map((a, i) => (
              <div key={i} style={styles.anomalyRow}>
                <div style={styles.anomalyLeft}>
                  <span style={{ ...styles.anomalyIcon, color: a.direction === "spike" ? "#f59e0b" : "#ef4444" }}>
                    {a.direction === "spike" ? "↑" : "↓"}
                  </span>
                  <div>
                    <span style={styles.anomalyName}>{a.product_name}</span>
                    <span style={styles.anomalyMeta}>
                      {a.anomaly_date} · {a.direction} {a.pct_deviation.toFixed(0)}% · sold {a.actual_qty} vs {a.expected_qty} expected
                    </span>
                  </div>
                </div>
                <p style={styles.anomalyExplanation}>{a.explanation}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </PageShell>
  );
}

const styles: Record<string, React.CSSProperties> = {
  errorBanner: { background: "#ef444418", border: "1px solid #ef444444", borderRadius: "var(--radius)", padding: "12px 16px", marginBottom: 20, color: "var(--danger)", fontSize: 13 },
  grid: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 28 },
  card: {
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderTop: "3px solid",
    borderRadius: "var(--radius)",
    padding: "20px 22px",
  },
  cardLabel: { color: "var(--text-muted)", fontSize: 12, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.5px" },
  cardValue: { fontSize: 26, fontWeight: 700 },
  row: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 },
  panel: {
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    padding: "20px 22px",
    minHeight: 200,
  },
  panelTitle: { fontWeight: 600, fontSize: 14, marginBottom: 14 },
  muted: { color: "var(--text-muted)", fontSize: 13, paddingTop: 8 },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { textAlign: "left", padding: "6px 10px", color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.5px", fontWeight: 600 },
  tr: { borderTop: "1px solid var(--border)" },
  td: { padding: "9px 10px", fontSize: 13 },
  badge: { padding: "2px 8px", borderRadius: 100, fontSize: 11, fontWeight: 700 },
  alertList: { display: "flex", flexDirection: "column", gap: 10 },
  alertRow: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 12px", background: "var(--surface2)", borderRadius: 6, border: "1px solid #ef444430" },
  alertName: { fontWeight: 600, fontSize: 13, display: "block" },
  alertSub: { color: "var(--danger)", fontSize: 12, display: "block", marginTop: 2 },
  alertMeta: { display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 },
  reorderBadge: { background: "#ef444422", color: "#ef4444", fontSize: 10, fontWeight: 700, padding: "2px 7px", borderRadius: 100 },
  alertDate: { color: "var(--text-muted)", fontSize: 11 },
  anomalyBadge: { marginLeft: 10, fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 100, background: "#f59e0b22", color: "#f59e0b" },
  anomalyList: { display: "flex", flexDirection: "column", gap: 12 },
  anomalyRow: { padding: "12px 14px", background: "var(--surface2)", borderRadius: 6, border: "1px solid var(--border)" },
  anomalyLeft: { display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 6 },
  anomalyIcon: { fontSize: 18, fontWeight: 700, lineHeight: 1, marginTop: 1 },
  anomalyName: { fontWeight: 600, fontSize: 13, display: "block" },
  anomalyMeta: { fontSize: 11, color: "var(--text-muted)", display: "block", marginTop: 2 },
  anomalyExplanation: { fontSize: 13, color: "var(--text-muted)", lineHeight: 1.5, marginLeft: 28 },
};
