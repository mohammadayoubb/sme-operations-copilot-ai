import { useState } from "react";
import PageShell from "../components/PageShell";

export default function Orders() {
  const [message, setMessage] = useState("");

  return (
    <PageShell title="Orders" subtitle="Paste a WhatsApp or Instagram order — AI extracts the structured order automatically">
      <div style={styles.card}>
        <label style={styles.label}>Paste customer message</label>
        <textarea
          style={styles.textarea}
          rows={5}
          placeholder={"e.g. Salam, I want 2 black hoodies size M, delivery to Hamra, cash on delivery"}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
        />
        <button style={styles.btn} disabled={!message.trim()}>
          Extract Order with AI
        </button>
      </div>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Extracted Order</h3>
        <div style={styles.emptyState}>
          Paste a customer message above and click extract to see the structured order here.
        </div>
      </div>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Recent Orders</h3>
        <div style={styles.emptyState}>No orders yet.</div>
      </div>
    </PageShell>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    padding: "24px",
    marginBottom: 28,
  },
  label: { display: "block", fontWeight: 600, marginBottom: 10, fontSize: 14 },
  textarea: {
    width: "100%",
    background: "var(--surface2)",
    border: "1px solid var(--border)",
    borderRadius: 6,
    padding: "12px 14px",
    color: "var(--text)",
    resize: "vertical",
    marginBottom: 14,
  },
  btn: {
    background: "var(--accent)",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    padding: "10px 24px",
    fontWeight: 600,
    fontSize: 14,
    opacity: 1,
  },
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
