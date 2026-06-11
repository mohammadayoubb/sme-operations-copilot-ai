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
  confidence_score: number | null;
  review_status: string | null;
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
  confidence_score: number | null;
  review_status: string | null;
  created_at: string | null;
}

const STATUS_OPTIONS = ["pending", "confirmed", "fulfilled", "cancelled"];

function ConfidenceBadge({ score }: { score: number | null }) {
  if (score === null) return null;
  const pct = Math.round(score * 100);
  const isHigh = score >= 0.75;
  const isMed = score >= 0.50;
  const color = isHigh ? "#34d399" : isMed ? "#f59e0b" : "#ef4444";
  const bg = isHigh ? "rgba(52,211,153,0.12)" : isMed ? "rgba(245,158,11,0.12)" : "rgba(239,68,68,0.12)";
  const border = isHigh ? "rgba(52,211,153,0.3)" : isMed ? "rgba(245,158,11,0.3)" : "rgba(239,68,68,0.3)";
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      background: bg, border: `1px solid ${border}`,
      borderRadius: 100, padding: "3px 10px", fontSize: 12, fontWeight: 600, color,
    }}>
      <span style={{ width: 7, height: 7, borderRadius: "50%", background: color, display: "inline-block" }} />
      {pct}% confidence
    </span>
  );
}

function ReviewQueue({
  queue,
  onApprove,
  onReject,
}: {
  queue: OrderDetail[];
  onApprove: (id: number) => void;
  onReject: (id: number) => void;
}) {
  if (queue.length === 0) return null;

  return (
    <div style={styles.reviewSection}>
      <div style={styles.reviewHeader}>
        <div style={styles.reviewTitleRow}>
          <span style={styles.reviewDot} />
          <h3 style={styles.reviewTitle}>Human Review Queue</h3>
          <span style={styles.reviewCount}>{queue.length}</span>
        </div>
        <p style={styles.reviewSubtitle}>
          Low-confidence extractions — review before inventory is committed
        </p>
      </div>

      <div style={styles.reviewList}>
        {queue.map((order) => {
          const extracted = order.extracted_json || {};
          const intent = (extracted.intent as string) ?? "—";
          const items = order.items;

          return (
            <div key={order.id} style={styles.reviewCard}>
              <div style={styles.reviewCardTop}>
                <div style={styles.reviewCardMeta}>
                  <span style={styles.reviewOrderId}>Order #{order.id}</span>
                  <ConfidenceBadge score={order.confidence_score} />
                  <span style={styles.reviewSource}>{order.source ?? "—"}</span>
                </div>
                <div style={styles.reviewActions}>
                  <button
                    style={styles.rejectBtn}
                    onClick={() => onReject(order.id)}
                  >
                    Reject
                  </button>
                  <button
                    style={styles.approveBtn}
                    onClick={() => onApprove(order.id)}
                  >
                    Approve &amp; Commit
                  </button>
                </div>
              </div>

              {order.raw_message && (
                <div style={styles.rawMessage}>
                  <span style={styles.rawLabel}>Message</span>
                  <span style={styles.rawText}>{order.raw_message}</span>
                </div>
              )}

              <div style={styles.reviewExtracted}>
                <div style={styles.reviewField}>
                  <span style={styles.fieldLabel}>Intent</span>
                  <span style={styles.fieldValue}>{intent}</span>
                </div>
                <div style={styles.reviewField}>
                  <span style={styles.fieldLabel}>Delivery</span>
                  <span style={styles.fieldValue}>{order.delivery_area ?? "—"}</span>
                </div>
                <div style={styles.reviewField}>
                  <span style={styles.fieldLabel}>Payment</span>
                  <span style={styles.fieldValue}>{order.payment_method ?? "—"}</span>
                </div>
              </div>

              {items.length > 0 && (
                <table style={styles.table}>
                  <thead>
                    <tr>
                      {["Product", "Qty", "Color", "Size"].map((h) => (
                        <th key={h} style={styles.th}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((it) => (
                      <tr key={it.id} style={styles.tr}>
                        <td style={styles.td}>{it.product_name}</td>
                        <td style={styles.td}>{it.quantity}</td>
                        <td style={styles.td}>{it.color ?? "—"}</td>
                        <td style={styles.td}>{it.size ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function Orders() {
  const [message, setMessage] = useState("");
  const [source, setSource] = useState("whatsapp");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OrderDetail | null>(null);
  const [orders, setOrders] = useState<OrderListRow[]>([]);
  const [reviewQueue, setReviewQueue] = useState<OrderDetail[]>([]);

  async function loadOrders() {
    try {
      const { data } = await ordersApi.list();
      setOrders(data);
    } catch {
      /* non-fatal */
    }
  }

  async function loadReviewQueue() {
    try {
      const { data } = await ordersApi.reviewQueue();
      setReviewQueue(data);
    } catch {
      /* non-fatal */
    }
  }

  useEffect(() => {
    loadOrders();
    loadReviewQueue();
  }, []);

  async function handleExtract() {
    setError(null);
    setResult(null);
    setBusy(true);
    try {
      const { data } = await ordersApi.extract(message, source);
      setResult(data);
      await Promise.all([loadOrders(), loadReviewQueue()]);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Extraction failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleApprove(id: number) {
    try {
      await ordersApi.approve(id);
      await Promise.all([loadOrders(), loadReviewQueue()]);
      if (result?.id === id) setResult({ ...result, review_status: "approved", status: "pending" });
    } catch (e: any) {
      alert(e?.response?.data?.detail ?? "Approval failed.");
    }
  }

  async function handleReject(id: number) {
    try {
      await ordersApi.reject(id);
      await Promise.all([loadOrders(), loadReviewQueue()]);
      if (result?.id === id) setResult({ ...result, review_status: "rejected", status: "cancelled" });
    } catch (e: any) {
      alert(e?.response?.data?.detail ?? "Rejection failed.");
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

      {/* Review Queue — shown when items are pending human approval */}
      <ReviewQueue queue={reviewQueue} onApprove={handleApprove} onReject={handleReject} />

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
                <span style={{
                  ...styles.metaValue,
                  color: result.review_status === "needs_review" ? "#f59e0b" : "var(--success)"
                }}>
                  {result.review_status === "needs_review" ? "Pending Review" : result.status}
                </span>
              </div>
              {result.confidence_score !== null && (
                <div>
                  <span style={styles.metaLabel}>Confidence</span>
                  <ConfidenceBadge score={result.confidence_score} />
                </div>
              )}
            </div>

            {result.review_status === "needs_review" && (
              <div style={styles.reviewWarning}>
                Low confidence extraction — this order is in the review queue above.
                Inventory will not be deducted until you approve it.
              </div>
            )}

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
                  {["#", "Source", "Delivery", "Payment", "Confidence", "Created", "Status"].map((h) => (
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
                    <td style={styles.td}>
                      {o.review_status === "needs_review"
                        ? <ConfidenceBadge score={o.confidence_score} />
                        : <span style={{ color: "var(--text-muted)", fontSize: 12 }}>
                            {o.confidence_score !== null ? `${Math.round((o.confidence_score ?? 1) * 100)}%` : "—"}
                          </span>
                      }
                    </td>
                    <td style={styles.td}>{o.created_at ? new Date(o.created_at).toLocaleString() : "—"}</td>
                    <td style={styles.td}>
                      {o.review_status === "needs_review" ? (
                        <span style={{ color: "#f59e0b", fontSize: 12, fontWeight: 600 }}>Review Queue</span>
                      ) : (
                        <select
                          style={styles.statusSelect}
                          value={o.status}
                          onChange={(e) => changeStatus(o.id, e.target.value)}
                        >
                          {STATUS_OPTIONS.map((s) => (
                            <option key={s} value={s}>{s}</option>
                          ))}
                        </select>
                      )}
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
    cursor: "pointer",
  },
  errorBanner: {
    background: "#ef444418", border: "1px solid #ef444444", borderRadius: "var(--radius)",
    padding: "12px 16px", marginBottom: 20, color: "var(--danger)", fontSize: 13,
  },

  // Review Queue
  reviewSection: {
    border: "1px solid rgba(245,158,11,0.3)",
    borderRadius: "var(--radius)",
    background: "rgba(245,158,11,0.04)",
    marginBottom: 28,
    overflow: "hidden",
  },
  reviewHeader: {
    padding: "16px 20px 12px",
    borderBottom: "1px solid rgba(245,158,11,0.15)",
    background: "rgba(245,158,11,0.06)",
  },
  reviewTitleRow: { display: "flex", alignItems: "center", gap: 10, marginBottom: 4 },
  reviewDot: {
    width: 8, height: 8, borderRadius: "50%", background: "#f59e0b", display: "inline-block",
    boxShadow: "0 0 6px #f59e0b",
  },
  reviewTitle: { fontWeight: 700, fontSize: 14, color: "#f59e0b", margin: 0 },
  reviewCount: {
    background: "rgba(245,158,11,0.2)", border: "1px solid rgba(245,158,11,0.4)",
    borderRadius: 100, padding: "1px 8px", fontSize: 12, fontWeight: 700, color: "#f59e0b",
  },
  reviewSubtitle: { color: "rgba(255,255,255,0.4)", fontSize: 12, margin: 0 },
  reviewList: { padding: "12px 16px", display: "flex", flexDirection: "column", gap: 12 },
  reviewCard: {
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: 8,
    overflow: "hidden",
  },
  reviewCardTop: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    padding: "12px 16px", borderBottom: "1px solid var(--border)", flexWrap: "wrap", gap: 10,
  },
  reviewCardMeta: { display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" },
  reviewOrderId: { fontWeight: 700, fontSize: 13 },
  reviewSource: {
    color: "var(--text-muted)", fontSize: 12,
    background: "var(--surface2)", borderRadius: 4, padding: "2px 7px",
  },
  reviewActions: { display: "flex", gap: 8 },
  rejectBtn: {
    background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
    color: "#ef4444", borderRadius: 6, padding: "6px 14px", fontSize: 13, fontWeight: 600, cursor: "pointer",
  },
  approveBtn: {
    background: "rgba(52,211,153,0.15)", border: "1px solid rgba(52,211,153,0.35)",
    color: "#34d399", borderRadius: 6, padding: "6px 14px", fontSize: 13, fontWeight: 600, cursor: "pointer",
  },
  rawMessage: {
    padding: "10px 16px", borderBottom: "1px solid var(--border)",
    background: "var(--surface2)", display: "flex", flexDirection: "column", gap: 3,
  },
  rawLabel: { fontSize: 10, textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", fontWeight: 600 },
  rawText: { fontSize: 13, color: "var(--text)", fontStyle: "italic" },
  reviewExtracted: {
    display: "flex", gap: 24, padding: "12px 16px", borderBottom: "1px solid var(--border)", flexWrap: "wrap",
  },
  reviewField: { display: "flex", flexDirection: "column", gap: 2 },
  fieldLabel: { fontSize: 10, textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", fontWeight: 600 },
  fieldValue: { fontSize: 13, fontWeight: 500 },

  reviewWarning: {
    background: "rgba(245,158,11,0.08)", border: "none", borderBottom: "1px solid rgba(245,158,11,0.2)",
    padding: "10px 20px", fontSize: 13, color: "#f59e0b",
  },

  section: { marginBottom: 28 },
  sectionTitle: { fontWeight: 600, marginBottom: 12, fontSize: 15 },
  resultCard: {
    background: "var(--surface)", border: "1px solid var(--border)",
    borderRadius: "var(--radius)", overflow: "hidden",
  },
  resultHeader: {
    display: "flex", gap: 32, padding: "16px 20px",
    borderBottom: "1px solid var(--border)", background: "var(--surface2)", flexWrap: "wrap",
  },
  metaLabel: {
    display: "block", color: "var(--text-muted)", fontSize: 11,
    textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 4,
  },
  metaValue: { fontWeight: 600, fontSize: 14 },
  table: { width: "100%", borderCollapse: "collapse" },
  th: {
    textAlign: "left", padding: "10px 16px", color: "var(--text-muted)",
    fontSize: 12, textTransform: "uppercase", letterSpacing: "0.5px", fontWeight: 600,
  },
  tr: { borderTop: "1px solid var(--border)" },
  td: { padding: "11px 16px", fontSize: 14 },
  noItems: { padding: "16px 20px", color: "var(--text-muted)", fontSize: 13 },
  jsonWrap: { borderTop: "1px solid var(--border)", padding: "12px 20px" },
  jsonSummary: { cursor: "pointer", color: "var(--text-muted)", fontSize: 13 },
  json: {
    background: "var(--surface2)", border: "1px solid var(--border)",
    borderRadius: 6, padding: 14, fontSize: 12.5, overflowX: "auto", marginTop: 10,
  },
  statusSelect: {
    background: "#1a1d2e", border: "1px solid rgba(255,255,255,0.18)",
    borderRadius: 6, padding: "5px 8px", color: "var(--text)", fontSize: 13,
  },
  emptyState: {
    background: "var(--surface)", border: "1px solid var(--border)",
    borderRadius: "var(--radius)", padding: "24px", color: "var(--text-muted)", textAlign: "center",
  },
};
