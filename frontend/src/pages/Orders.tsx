import { useEffect, useState } from "react";
import PageShell from "../components/PageShell";
import { ordersApi } from "../services/api";

interface OrderItem {
  id: number;
  product_id: number | null;
  product_name: string | null;
  quantity: number | null;
  color: string | null;
  size: string | null;
  notes: string | null;
}

interface OrderDetail {
  id: number;
  source: string | null;
  delivery_area: string | null;
  payment_method: string | null;
  status: string;
  created_at: string | null;
  raw_message: string | null;
  extracted_json: Record<string, unknown> | null;
  items: OrderItem[];
}

interface OrderListRow {
  id: number;
  source: string | null;
  delivery_area: string | null;
  payment_method: string | null;
  status: string;
  created_at: string | null;
}

const STATUS_OPTIONS = ["pending", "confirmed", "fulfilled", "cancelled"];

export default function Orders() {
  const [message, setMessage] = useState("");
  const [source, setSource] = useState("whatsapp");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OrderDetail | null>(null);
  const [orders, setOrders] = useState<OrderListRow[]>([]);

  async function loadOrders() {
    try {
      const { data } = await ordersApi.list();
      setOrders(data);
    } catch {
      /* non-fatal: list just stays as-is */
    }
  }

  useEffect(() => {
    loadOrders();
  }, []);

  async function handleExtract() {
    setError(null);
    setResult(null);
    setBusy(true);
    try {
      const { data } = await ordersApi.extract(message, source);
      setResult(data);
      await loadOrders();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Extraction failed.");
    } finally {
      setBusy(false);
    }
  }

  async function changeStatus(id: number, status: string) {
    try {
      await ordersApi.updateStatus(id, status);
      await loadOrders();
      if (result?.id === id) setResult({ ...result, status });
    } catch {
      /* ignore */
    }
  }

  return (
    <PageShell title="Orders" subtitle="Paste a WhatsApp or Instagram order — AI extracts the structured order automatically">
      <div style={styles.card}>
        <label style={styles.label}>Paste customer message</label>
        <textarea
          style={styles.textarea}
          rows={5}
          placeholder={"e.g. Salam, bddi 3 black hoodies size L w 2 white ones size M, delivery to Hamra, cash on delivery"}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
        />
        <div style={styles.controls}>
          <select style={styles.select} value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="whatsapp">WhatsApp</option>
            <option value="instagram">Instagram</option>
            <option value="manual">Manual</option>
          </select>
          <button style={styles.btn} disabled={!message.trim() || busy} onClick={handleExtract}>
            {busy ? "Extracting…" : "Extract Order with AI"}
          </button>
        </div>
      </div>

      {error && <div style={styles.errorBanner}>⚠ {error}</div>}

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Extracted Order</h3>
        {result ? (
          <div style={styles.resultCard}>
            <div style={styles.resultHeader}>
              <div>
                <span style={styles.metaLabel}>Intent</span>
                <span style={styles.metaValue}>{(result.extracted_json?.intent as string) ?? "—"}</span>
              </div>
              <div>
                <span style={styles.metaLabel}>Delivery Area</span>
                <span style={styles.metaValue}>{result.delivery_area ?? "—"}</span>
              </div>
              <div>
                <span style={styles.metaLabel}>Payment</span>
                <span style={styles.metaValue}>{result.payment_method ?? "—"}</span>
              </div>
              <div>
                <span style={styles.metaLabel}>Status</span>
                <span style={{ ...styles.metaValue, color: "var(--success)" }}>{result.status}</span>
              </div>
            </div>

            {result.items.length > 0 ? (
              <table style={styles.table}>
                <thead>
                  <tr>
                    {["Product", "Qty", "Color", "Size"].map((h) => (
                      <th key={h} style={styles.th}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.items.map((it) => (
                    <tr key={it.id} style={styles.tr}>
                      <td style={styles.td}>{it.product_name}</td>
                      <td style={styles.td}>{it.quantity}</td>
                      <td style={styles.td}>{it.color ?? "—"}</td>
                      <td style={styles.td}>{it.size ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div style={styles.noItems}>No order items (not a new order) — logged for follow-up.</div>
            )}

            <details style={styles.jsonWrap}>
              <summary style={styles.jsonSummary}>View extracted JSON</summary>
              <pre style={styles.json}>{JSON.stringify(result.extracted_json, null, 2)}</pre>
            </details>
          </div>
        ) : (
          <div style={styles.emptyState}>
            Paste a customer message above and click extract to see the structured order here.
          </div>
        )}
      </div>

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Recent Orders</h3>
        {orders.length > 0 ? (
          <div style={styles.resultCard}>
            <table style={styles.table}>
              <thead>
                <tr>
                  {["#", "Source", "Delivery", "Payment", "Created", "Status"].map((h) => (
                    <th key={h} style={styles.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => (
                  <tr key={o.id} style={styles.tr}>
                    <td style={styles.td}>{o.id}</td>
                    <td style={styles.td}>{o.source ?? "—"}</td>
                    <td style={styles.td}>{o.delivery_area ?? "—"}</td>
                    <td style={styles.td}>{o.payment_method ?? "—"}</td>
                    <td style={styles.td}>{o.created_at ? new Date(o.created_at).toLocaleString() : "—"}</td>
                    <td style={styles.td}>
                      <select
                        style={styles.statusSelect}
                        value={o.status}
                        onChange={(e) => changeStatus(o.id, e.target.value)}
                      >
                        {STATUS_OPTIONS.map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={styles.emptyState}>No orders yet.</div>
        )}
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
  controls: { display: "flex", gap: 12, alignItems: "center" },
  select: {
    background: "#1a1d2e",
    border: "1px solid rgba(255,255,255,0.18)",
    borderRadius: 6,
    padding: "10px 12px",
    color: "var(--text)",
    fontSize: 14,
  },
  btn: {
    background: "var(--accent)",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    padding: "10px 24px",
    fontWeight: 600,
    fontSize: 14,
  },
  errorBanner: { background: "#ef444418", border: "1px solid #ef444444", borderRadius: "var(--radius)", padding: "12px 16px", marginBottom: 20, color: "var(--danger)", fontSize: 13 },
  section: { marginBottom: 28 },
  sectionTitle: { fontWeight: 600, marginBottom: 12, fontSize: 15 },
  resultCard: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", overflow: "hidden" },
  resultHeader: { display: "flex", gap: 32, padding: "16px 20px", borderBottom: "1px solid var(--border)", background: "var(--surface2)", flexWrap: "wrap" },
  metaLabel: { display: "block", color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 2 },
  metaValue: { fontWeight: 600, fontSize: 14 },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { textAlign: "left", padding: "10px 16px", color: "var(--text-muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.5px", fontWeight: 600 },
  tr: { borderTop: "1px solid var(--border)" },
  td: { padding: "11px 16px", fontSize: 14 },
  noItems: { padding: "16px 20px", color: "var(--text-muted)", fontSize: 13 },
  jsonWrap: { borderTop: "1px solid var(--border)", padding: "12px 20px" },
  jsonSummary: { cursor: "pointer", color: "var(--text-muted)", fontSize: 13 },
  json: { background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: 6, padding: 14, fontSize: 12.5, overflowX: "auto", marginTop: 10 },
  statusSelect: {
    background: "#1a1d2e",
    border: "1px solid rgba(255,255,255,0.18)",
    borderRadius: 6,
    padding: "5px 8px",
    color: "var(--text)",
    fontSize: 13,
  },
  emptyState: {
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    padding: "24px",
    color: "var(--text-muted)",
    textAlign: "center",
  },
};
