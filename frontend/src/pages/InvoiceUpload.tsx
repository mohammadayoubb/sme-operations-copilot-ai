import PageShell from "../components/PageShell";

export default function InvoiceUpload() {
  return (
    <PageShell title="Invoice Upload" subtitle="Upload a supplier invoice — OCR + AI extracts the structured data automatically">
      <div style={styles.uploadBox}>
        <div style={styles.uploadIcon}>📄</div>
        <p style={styles.uploadText}>Drag & drop an invoice image or PDF here</p>
        <p style={styles.uploadSub}>or</p>
        <button style={styles.btn}>Choose File</button>
        <p style={styles.hint}>Supported: JPG, PNG, PDF · Max 20 MB</p>
      </div>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Extracted Result</h3>
        <div style={styles.emptyState}>
          Upload an invoice above to see the AI-extracted structured data here.
        </div>
      </div>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Recent Invoices</h3>
        <div style={styles.emptyState}>No invoices processed yet.</div>
      </div>
    </PageShell>
  );
}

const styles: Record<string, React.CSSProperties> = {
  uploadBox: {
    background: "var(--surface)",
    border: "2px dashed var(--border)",
    borderRadius: "var(--radius)",
    padding: "48px 32px",
    textAlign: "center",
    marginBottom: 28,
  },
  uploadIcon: { fontSize: 48, marginBottom: 12 },
  uploadText: { fontWeight: 600, fontSize: 16, marginBottom: 8 },
  uploadSub: { color: "var(--text-muted)", marginBottom: 16 },
  btn: {
    background: "var(--accent)",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    padding: "10px 24px",
    fontWeight: 600,
    fontSize: 14,
  },
  hint: { color: "var(--text-muted)", fontSize: 12, marginTop: 12 },
  section: { marginBottom: 28 },
  sectionTitle: { fontWeight: 600, marginBottom: 12, fontSize: 15 },
  emptyState: {
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    padding: "24px",
    color: "var(--text-muted)",
    textAlign: "center",
  },
};
