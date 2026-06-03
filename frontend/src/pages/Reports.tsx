import { useEffect, useState } from "react";
import PageShell from "../components/PageShell";
import { reportsApi } from "../services/api";

interface Pair { this_week: number; last_week: number; change_pct: number | null; }
interface TopProduct { name: string; revenue: number; units: number; }
interface Risk { name: string; current_stock: number; days_until_stockout: number | null; }
interface Margin { name: string; margin_pct: number | null; }

interface ReportData {
  period: { start: string; end: string };
  sales: Pair;
  profit: Pair;
  top_products: TopProduct[];
  low_stock_risks: Risk[];
  supplier_price_changes: { supplier: string; product: string; change_pct: number }[];
  most_profitable: Margin | null;
  least_profitable: Margin | null;
}

interface Report {
  id: number;
  period_start: string | null;
  period_end: string | null;
  report_type: string;
  summary_text: string | null;
  data_json: ReportData | null;
  created_at: string | null;
}

interface ReportRow {
  id: number;
  period_start: string | null;
  period_end: string | null;
  report_type: string;
  created_at: string | null;
}

function ChangeBadge({ pct }: { pct: number | null }) {
  if (pct == null) return <span style={{ color: "var(--text-muted)", fontSize: 12 }}>— no prior week</span>;
  const up = pct >= 0;
  return (
    <span style={{ color: up ? "var(--success)" : "var(--danger)", fontSize: 12, fontWeight: 600 }}>
      {up ? "▲" : "▼"} {Math.abs(pct)}% vs last week
    </span>
  );
}

export default function Reports() {
  const [latest, setLatest] = useState<Report | null>(null);
  const [history, setHistory] = useState<ReportRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const list = await reportsApi.list();
      setHistory(list.data);
      if (list.data.length > 0) {
        const l = await reportsApi.latest();
        setLatest(l.data);
      }
    } catch {
      /* nothing yet */
    }
  }

  useEffect(() => { load(); }, []);

  async function generate() {
    setError(null);
    setBusy(true);
    try {
      const { data } = await reportsApi.generate();
      setLatest(data);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Report generation failed.");
    } finally {
      setBusy(false);
    }
  }

  const d = latest?.data_json ?? null;

  return (
    <PageShell title="Weekly Reports" subtitle="AI-generated business summaries — numbers computed in code, narrative written by AI. Auto-runs every Monday at 8 AM.">
      <div style={styles.toolbar}>
        <button style={{ ...styles.btn, opacity: busy ? 0.6 : 1 }} disabled={busy} onClick={generate}>
          {busy ? "Generating…" : "Generate Report Now"}
        </button>
      </div>

      {error && <div style={styles.errorBanner}>⚠ {error}</div>}

      {latest && d ? (
        <>
          <div style={styles.reportCard}>
            <div style={styles.reportHeader}>
              <span style={styles.reportTitle}>📊 Week of {d.period.start} → {d.period.end}</span>
              <span style={styles.reportType}>{latest.report_type}</span>
            </div>
            <p style={styles.summary}>{latest.summary_text}</p>
          </div>

          <div style={styles.metrics}>
            <div style={styles.metricCard}>
              <span style={styles.metricLabel}>Sales (this week)</span>
              <span style={styles.metricValue}>${d.sales.this_week.toFixed(2)}</span>
              <ChangeBadge pct={d.sales.change_pct} />
            </div>
            <div style={styles.metricCard}>
              <span style={styles.metricLabel}>Profit (this week)</span>
              <span style={{ ...styles.metricValue, color: d.profit.this_week >= 0 ? "var(--success)" : "var(--danger)" }}>
                ${d.profit.this_week.toFixed(2)}
              </span>
              <ChangeBadge pct={d.profit.change_pct} />
            </div>
            <div style={styles.metricCard}>
              <span style={styles.metricLabel}>Most profitable</span>
              <span style={styles.metricValueSm}>{d.most_profitable?.name ?? "—"}</span>
              <span style={styles.metricSub}>{d.most_profitable?.margin_pct != null ? `${d.most_profitable.margin_pct}% margin` : ""}</span>
            </div>
            <div style={styles.metricCard}>
              <span style={styles.metricLabel}>Least profitable</span>
              <span style={styles.metricValueSm}>{d.least_profitable?.name ?? "—"}</span>
              <span style={styles.metricSub}>{d.least_profitable?.margin_pct != null ? `${d.least_profitable.margin_pct}% margin` : ""}</span>
            </div>
          </div>

          <div style={styles.cols}>
            <div style={styles.col}>
              <h3 style={styles.colTitle}>Top Products by Revenue</h3>
              <div style={styles.listCard}>
                {d.top_products.length ? d.top_products.map((p) => (
                  <div key={p.name} style={styles.row}>
                    <span>{p.name}</span>
                    <span style={styles.rowValue}>${p.revenue.toFixed(2)} · {p.units} units</span>
                  </div>
                )) : <div style={styles.muted}>No sales this week.</div>}
              </div>
            </div>
            <div style={styles.col}>
              <h3 style={styles.colTitle}>Reorder Risks</h3>
              <div style={styles.listCard}>
                {d.low_stock_risks.length ? d.low_stock_risks.map((r) => (
                  <div key={r.name} style={styles.row}>
                    <span>{r.name}</span>
                    <span style={{ ...styles.rowValue, color: "var(--danger)" }}>
                      {r.days_until_stockout != null ? `${r.days_until_stockout}d left` : `stock ${r.current_stock}`}
                    </span>
                  </div>
                )) : <div style={styles.muted}>Nothing at risk. 🎉</div>}
              </div>
            </div>
          </div>

          {history.length > 1 && (
            <div style={styles.col}>
              <h3 style={styles.colTitle}>Report History</h3>
              <div style={styles.listCard}>
                {history.map((h) => (
                  <div key={h.id} style={styles.row}>
                    <span>Week of {h.period_start} → {h.period_end}</span>
                    <span style={styles.muted}>{h.created_at ? new Date(h.created_at).toLocaleString() : ""}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <div style={styles.emptyState}>
          <div style={styles.emptyIcon}>📊</div>
          <p style={styles.emptyTitle}>No reports yet</p>
          <p style={styles.emptySub}>
            Click "Generate Report Now" or wait for the scheduled Monday report. Reports summarise sales, profit, supplier price changes, and reorder risks.
          </p>
        </div>
      )}
    </PageShell>
  );
}

const styles: Record<string, React.CSSProperties> = {
  toolbar: { marginBottom: 24 },
  btn: { background: "var(--accent)", color: "#fff", border: "none", borderRadius: 6, padding: "10px 24px", fontWeight: 600, fontSize: 14 },
  errorBanner: { background: "#ef444418", border: "1px solid #ef444444", borderRadius: "var(--radius)", padding: "12px 16px", marginBottom: 20, color: "var(--danger)", fontSize: 13 },
  reportCard: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "20px 22px", marginBottom: 20 },
  reportHeader: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  reportTitle: { fontWeight: 700, fontSize: 15 },
  reportType: { fontSize: 10, fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.5px", border: "1px solid var(--border)", borderRadius: 100, padding: "3px 10px" },
  summary: { fontSize: 14, lineHeight: 1.7 },
  metrics: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 24 },
  metricCard: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "16px 18px", display: "flex", flexDirection: "column", gap: 6 },
  metricLabel: { color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.5px" },
  metricValue: { fontWeight: 700, fontSize: 22 },
  metricValueSm: { fontWeight: 700, fontSize: 15 },
  metricSub: { color: "var(--text-muted)", fontSize: 12 },
  cols: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 },
  col: { marginBottom: 8 },
  colTitle: { fontWeight: 600, marginBottom: 10, fontSize: 14 },
  listCard: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", overflow: "hidden" },
  row: { display: "flex", justifyContent: "space-between", padding: "11px 16px", fontSize: 13.5, borderTop: "1px solid var(--border)" },
  rowValue: { fontWeight: 600 },
  muted: { color: "var(--text-muted)", fontSize: 13, padding: "11px 16px" },
  emptyState: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "48px 32px", textAlign: "center" },
  emptyIcon: { fontSize: 48, marginBottom: 16 },
  emptyTitle: { fontWeight: 600, fontSize: 16, marginBottom: 8 },
  emptySub: { color: "var(--text-muted)", maxWidth: 420, margin: "0 auto", fontSize: 13, lineHeight: 1.7 },
};
