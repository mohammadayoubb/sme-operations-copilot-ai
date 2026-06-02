import PageShell from "../components/PageShell";

const MOCK_PRODUCTS = [
  { name: "Pepsi 330ml",   stock: 24, reorder: 20, status: "ok" },
  { name: "Nutella 400g",  stock: 6,  reorder: 10, status: "low" },
  { name: "Lays Chips",    stock: 48, reorder: 30, status: "ok" },
  { name: "Water 1.5L",    stock: 3,  reorder: 15, status: "critical" },
];

const STATUS_COLORS: Record<string, string> = {
  ok: "#22c55e",
  low: "#f59e0b",
  critical: "#ef4444",
};

export default function Inventory() {
  return (
    <PageShell title="Inventory" subtitle="Live stock levels — updated automatically when invoices or orders are processed">
      <div style={styles.alertBanner}>
        <span style={styles.alertIcon}>⚠</span>
        <span><strong>2 products</strong> are below reorder level — showing demo data</span>
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
          {MOCK_PRODUCTS.map((p) => (
            <tr key={p.name} style={styles.tr}>
              <td style={styles.td}>{p.name}</td>
              <td style={styles.td}>{p.stock}</td>
              <td style={styles.td}>{p.reorder}</td>
              <td style={styles.td}>
                <span style={{ ...styles.badge, background: STATUS_COLORS[p.status] + "22", color: STATUS_COLORS[p.status] }}>
                  {p.status.toUpperCase()}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </PageShell>
  );
}

const styles: Record<string, React.CSSProperties> = {
  alertBanner: {
    background: "#f59e0b18",
    border: "1px solid #f59e0b44",
    borderRadius: "var(--radius)",
    padding: "12px 16px",
    marginBottom: 24,
    display: "flex",
    alignItems: "center",
    gap: 10,
    color: "#f59e0b",
    fontSize: 13,
  },
  alertIcon: { fontSize: 16 },
  table: { width: "100%", borderCollapse: "collapse", background: "var(--surface)", borderRadius: "var(--radius)", overflow: "hidden" },
  th: { textAlign: "left", padding: "12px 16px", background: "var(--surface2)", color: "var(--text-muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.5px", fontWeight: 600 },
  tr: { borderBottom: "1px solid var(--border)" },
  td: { padding: "13px 16px", fontSize: 14 },
  badge: { padding: "3px 10px", borderRadius: 100, fontSize: 11, fontWeight: 700 },
};
