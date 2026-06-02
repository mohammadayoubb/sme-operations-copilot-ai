import PageShell from "../components/PageShell";

const STAT_CARDS = [
  { label: "Total Sales (this week)", value: "—", color: "#6c63ff" },
  { label: "Gross Profit",            value: "—", color: "#22c55e" },
  { label: "Low Stock Alerts",        value: "—", color: "#f59e0b" },
  { label: "Pending Orders",          value: "—", color: "#ef4444" },
];

export default function Dashboard() {
  return (
    <PageShell title="Dashboard" subtitle="Your business at a glance">
      <div style={styles.grid}>
        {STAT_CARDS.map((c) => (
          <div key={c.label} style={{ ...styles.card, borderTopColor: c.color }}>
            <p style={styles.cardLabel}>{c.label}</p>
            <p style={{ ...styles.cardValue, color: c.color }}>{c.value}</p>
          </div>
        ))}
      </div>

      <div style={styles.row}>
        <Placeholder label="Recent Invoices" />
        <Placeholder label="Reorder Alerts" />
      </div>
    </PageShell>
  );
}

function Placeholder({ label }: { label: string }) {
  return (
    <div style={styles.placeholder}>
      <p style={styles.placeholderLabel}>{label}</p>
      <p style={styles.placeholderSub}>Data will appear here once connected to the backend.</p>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  grid: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 28 },
  card: {
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderTop: "3px solid",
    borderRadius: "var(--radius)",
    padding: "20px 22px",
  },
  cardLabel: { color: "var(--text-muted)", fontSize: 12, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.5px" },
  cardValue: { fontSize: 28, fontWeight: 700 },
  row: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 },
  placeholder: {
    background: "var(--surface)",
    border: "1px dashed var(--border)",
    borderRadius: "var(--radius)",
    padding: "32px 24px",
    textAlign: "center",
  },
  placeholderLabel: { fontWeight: 600, marginBottom: 8 },
  placeholderSub: { color: "var(--text-muted)", fontSize: 13 },
};
