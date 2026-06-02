import { useEffect, useState } from "react";
import PageShell from "../components/PageShell";
import { forecastApi, productsApi } from "../services/api";

interface Product {
  id: number;
  name: string;
  current_stock: number | null;
  reorder_level: number | null;
}

interface Forecast {
  product_id: number;
  product_name: string;
  current_stock: number;
  reorder_level: number;
  avg_daily_sales: number;
  days_until_stockout: number | null;
  reorder_recommended: boolean;
  reorder_by_date: string | null;
}

function statusOf(stock: number, reorder: number): "ok" | "low" | "critical" {
  if (stock <= 0) return "critical";
  if (stock <= reorder) return "low";
  return "ok";
}

const STATUS_COLORS: Record<string, string> = { ok: "#22c55e", low: "#f59e0b", critical: "#ef4444" };

export default function Inventory() {
  const [products, setProducts] = useState<Product[]>([]);
  const [reorders, setReorders] = useState<Forecast[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [p, r] = await Promise.all([productsApi.list(), forecastApi.reorder()]);
        setProducts(p.data);
        setReorders(r.data);
      } catch (e: any) {
        setError(e?.response?.data?.detail ?? "Failed to load inventory.");
      }
    })();
  }, []);

  const belowCount = products.filter(
    (p) => (p.current_stock ?? 0) <= (p.reorder_level ?? 0)
  ).length;

  return (
    <PageShell title="Inventory" subtitle="Live stock levels with AI demand forecasting — reorder before you run out">
      {error && <div style={styles.errorBanner}>⚠ {error}</div>}

      {reorders.length > 0 && (
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>🔮 Reorder Recommendations</h3>
          <div style={styles.cards}>
            {reorders.map((f) => (
              <div key={f.product_id} style={styles.alertCard}>
                <div style={styles.cardHeader}>
                  <span style={styles.cardName}>{f.product_name}</span>
                  <span style={styles.cardBadge}>REORDER</span>
                </div>
                <div style={styles.cardRow}>
                  <span style={styles.cardLabel}>Stock left</span>
                  <span style={styles.cardValue}>{f.current_stock}</span>
                </div>
                <div style={styles.cardRow}>
                  <span style={styles.cardLabel}>Avg sales/day</span>
                  <span style={styles.cardValue}>{f.avg_daily_sales}</span>
                </div>
                <div style={styles.cardRow}>
                  <span style={styles.cardLabel}>Runs out in</span>
                  <span style={{ ...styles.cardValue, color: "var(--danger)" }}>
                    {f.days_until_stockout != null ? `${f.days_until_stockout} days` : "—"}
                  </span>
                </div>
                <div style={styles.cardRow}>
                  <span style={styles.cardLabel}>Reorder by</span>
                  <span style={styles.cardValue}>{f.reorder_by_date ?? "now"}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>All Products</h3>
        <div style={styles.alertBanner}>
          <span style={styles.alertIcon}>⚠</span>
          <span><strong>{belowCount} product{belowCount === 1 ? "" : "s"}</strong> at or below reorder level</span>
        </div>

        <table style={styles.table}>
          <thead>
            <tr>
              {["Product", "Current Stock", "Reorder Level", "Status"].map((h) => (
                <th key={h} style={styles.th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {products.map((p) => {
              const stock = p.current_stock ?? 0;
              const reorder = p.reorder_level ?? 0;
              const st = statusOf(stock, reorder);
              return (
                <tr key={p.id} style={styles.tr}>
                  <td style={styles.td}>{p.name}</td>
                  <td style={styles.td}>{stock}</td>
                  <td style={styles.td}>{reorder}</td>
                  <td style={styles.td}>
                    <span style={{ ...styles.badge, background: STATUS_COLORS[st] + "22", color: STATUS_COLORS[st] }}>
                      {st.toUpperCase()}
                    </span>
                  </td>
                </tr>
              );
            })}
            {products.length === 0 && !error && (
              <tr><td style={styles.td} colSpan={4}>Loading…</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </PageShell>
  );
}

const styles: Record<string, React.CSSProperties> = {
  section: { marginBottom: 28 },
  sectionTitle: { fontWeight: 600, marginBottom: 12, fontSize: 15 },
  cards: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 14 },
  alertCard: { background: "var(--surface)", border: "1px solid #ef444444", borderRadius: "var(--radius)", padding: "16px 18px" },
  cardHeader: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  cardName: { fontWeight: 700, fontSize: 15 },
  cardBadge: { background: "#ef444422", color: "#ef4444", fontSize: 10, fontWeight: 700, padding: "3px 8px", borderRadius: 100 },
  cardRow: { display: "flex", justifyContent: "space-between", padding: "4px 0", fontSize: 13 },
  cardLabel: { color: "var(--text-muted)" },
  cardValue: { fontWeight: 600 },
  errorBanner: { background: "#ef444418", border: "1px solid #ef444444", borderRadius: "var(--radius)", padding: "12px 16px", marginBottom: 20, color: "var(--danger)", fontSize: 13 },
  alertBanner: { background: "#f59e0b18", border: "1px solid #f59e0b44", borderRadius: "var(--radius)", padding: "12px 16px", marginBottom: 16, display: "flex", alignItems: "center", gap: 10, color: "#f59e0b", fontSize: 13 },
  alertIcon: { fontSize: 16 },
  table: { width: "100%", borderCollapse: "collapse", background: "var(--surface)", borderRadius: "var(--radius)", overflow: "hidden" },
  th: { textAlign: "left", padding: "12px 16px", background: "var(--surface2)", color: "var(--text-muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.5px", fontWeight: 600 },
  tr: { borderBottom: "1px solid var(--border)" },
  td: { padding: "13px 16px", fontSize: 14 },
  badge: { padding: "3px 10px", borderRadius: 100, fontSize: 11, fontWeight: 700 },
};
