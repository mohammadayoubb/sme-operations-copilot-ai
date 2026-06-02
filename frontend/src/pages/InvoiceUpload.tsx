import { useRef, useState } from "react";
import PageShell from "../components/PageShell";
import { invoicesApi } from "../services/api";

interface ExtractedItem {
  product_name: string;
  quantity: number;
  unit_price: number;
  total: number;
  price_change_pct: number | null;
}

interface InvoiceDetail {
  id: number;
  supplier_id: number | null;
  invoice_date: string | null;
  invoice_total: number | null;
  currency: string | null;
  status: string;
  raw_ocr_text: string | null;
  items: ExtractedItem[];
}

type Phase = "idle" | "uploading" | "processing" | "done" | "failed";

export default function InvoiceUpload() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<InvoiceDetail | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function pollUntilDone(id: number) {
    for (let i = 0; i < 40; i++) {
      const { data } = await invoicesApi.status(id);
      if (data.status === "processed") {
        const detail = await invoicesApi.get(id);
        setResult(detail.data);
        setPhase("done");
        return;
      }
      if (data.status === "failed") {
        setError("Processing failed. Check the worker logs.");
        setPhase("failed");
        return;
      }
      await new Promise((r) => setTimeout(r, 1500));
    }
    setError("Timed out waiting for processing.");
    setPhase("failed");
  }

  async function handleFile(file: File) {
    setError(null);
    setResult(null);
    setPhase("uploading");
    try {
      const { data } = await invoicesApi.upload(file);
      setPhase("processing");
      await pollUntilDone(data.invoice_id);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Upload failed.");
      setPhase("failed");
    }
  }

  const busy = phase === "uploading" || phase === "processing";

  return (
    <PageShell title="Invoice Upload" subtitle="Upload a supplier invoice — OCR + AI extracts the structured data automatically">
      <div style={styles.uploadBox}>
        <div style={styles.uploadIcon}>📄</div>
        <p style={styles.uploadText}>Upload an invoice image or PDF</p>
        <input
          ref={fileRef}
          type="file"
          accept=".png,.jpg,.jpeg,.bmp,.tiff,.webp,.pdf"
          style={{ display: "none" }}
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />
        <button style={styles.btn} disabled={busy} onClick={() => fileRef.current?.click()}>
          {busy ? "Working…" : "Choose File"}
        </button>
        <p style={styles.hint}>Supported: JPG, PNG, PDF · Max 20 MB</p>
      </div>

      {phase === "processing" && (
        <div style={styles.statusBanner}>⏳ OCR + AI extraction running in the background…</div>
      )}
      {error && <div style={styles.errorBanner}>⚠ {error}</div>}

      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Extracted Result</h3>
        {result ? (
          <div style={styles.resultCard}>
            <div style={styles.resultHeader}>
              <div>
                <span style={styles.metaLabel}>Date</span>
                <span style={styles.metaValue}>{result.invoice_date ?? "—"}</span>
              </div>
              <div>
                <span style={styles.metaLabel}>Total</span>
                <span style={styles.metaValue}>{result.invoice_total ?? "—"} {result.currency}</span>
              </div>
              <div>
                <span style={styles.metaLabel}>Status</span>
                <span style={{ ...styles.metaValue, color: "var(--success)" }}>{result.status}</span>
              </div>
            </div>
            <table style={styles.table}>
              <thead>
                <tr>
                  {["Product", "Qty", "Unit Price", "Total", "Price Δ"].map((h) => (
                    <th key={h} style={styles.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.items.map((it, idx) => (
                  <tr key={idx} style={styles.tr}>
                    <td style={styles.td}>{it.product_name}</td>
                    <td style={styles.td}>{it.quantity}</td>
                    <td style={styles.td}>{it.unit_price}</td>
                    <td style={styles.td}>{it.total}</td>
                    <td style={styles.td}>
                      {it.price_change_pct != null ? (
                        <span style={{ color: it.price_change_pct >= 5 ? "var(--warning)" : "var(--text-muted)" }}>
                          {it.price_change_pct > 0 ? "+" : ""}{it.price_change_pct}%
                        </span>
                      ) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={styles.emptyState}>Upload an invoice above to see the AI-extracted data here.</div>
        )}
      </div>
    </PageShell>
  );
}

const styles: Record<string, React.CSSProperties> = {
  uploadBox: { background: "var(--surface)", border: "2px dashed var(--border)", borderRadius: "var(--radius)", padding: "48px 32px", textAlign: "center", marginBottom: 24 },
  uploadIcon: { fontSize: 48, marginBottom: 12 },
  uploadText: { fontWeight: 600, fontSize: 16, marginBottom: 16 },
  btn: { background: "var(--accent)", color: "#fff", border: "none", borderRadius: 6, padding: "10px 24px", fontWeight: 600, fontSize: 14 },
  hint: { color: "var(--text-muted)", fontSize: 12, marginTop: 12 },
  statusBanner: { background: "#6c63ff18", border: "1px solid #6c63ff44", borderRadius: "var(--radius)", padding: "12px 16px", marginBottom: 20, color: "var(--accent-hover)", fontSize: 13 },
  errorBanner: { background: "#ef444418", border: "1px solid #ef444444", borderRadius: "var(--radius)", padding: "12px 16px", marginBottom: 20, color: "var(--danger)", fontSize: 13 },
  section: { marginBottom: 28 },
  sectionTitle: { fontWeight: 600, marginBottom: 12, fontSize: 15 },
  resultCard: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", overflow: "hidden" },
  resultHeader: { display: "flex", gap: 32, padding: "16px 20px", borderBottom: "1px solid var(--border)", background: "var(--surface2)" },
  metaLabel: { display: "block", color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 2 },
  metaValue: { fontWeight: 600, fontSize: 14 },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { textAlign: "left", padding: "10px 16px", color: "var(--text-muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.5px", fontWeight: 600 },
  tr: { borderTop: "1px solid var(--border)" },
  td: { padding: "11px 16px", fontSize: 14 },
  emptyState: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 24, color: "var(--text-muted)", textAlign: "center" },
};
