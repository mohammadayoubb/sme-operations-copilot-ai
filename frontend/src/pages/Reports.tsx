import PageShell from "../components/PageShell";

export default function Reports() {
  return (
    <PageShell title="Weekly Reports" subtitle="AI-generated business summaries — automatically produced every Monday at 8 AM">
      <div style={styles.toolbar}>
        <button style={styles.btn}>Generate Report Now</button>
      </div>

      <div style={styles.emptyState}>
        <div style={styles.emptyIcon}>📊</div>
        <p style={styles.emptyTitle}>No reports yet</p>
        <p style={styles.emptySub}>
          Click "Generate Report Now" or wait for the scheduled Monday report. Reports summarise sales, profit, supplier price changes, and reorder risks.
        </p>
      </div>
    </PageShell>
  );
}

const styles: Record<string, React.CSSProperties> = {
  toolbar: { marginBottom: 24 },
  btn: { background: "var(--accent)", color: "#fff", border: "none", borderRadius: 6, padding: "10px 24px", fontWeight: 600, fontSize: 14 },
  emptyState: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "48px 32px", textAlign: "center" },
  emptyIcon: { fontSize: 48, marginBottom: 16 },
  emptyTitle: { fontWeight: 600, fontSize: 16, marginBottom: 8 },
  emptySub: { color: "var(--text-muted)", maxWidth: 420, margin: "0 auto", fontSize: 13, lineHeight: 1.7 },
};
