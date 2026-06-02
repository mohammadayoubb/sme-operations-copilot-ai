import { useState } from "react";
import PageShell from "../components/PageShell";
import { pricingApi } from "../services/api";

interface Form { cost: string; sell: string; delivery: string; packaging: string; }

interface Result {
  total_cost: number;
  profit: number;
  margin_pct: number;
  sell_for_25pct: number;
  explanation: string;
}

export default function PricingAdvisor() {
  const [form, setForm] = useState<Form>({ cost: "", sell: "", delivery: "", packaging: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Result | null>(null);

  const set = (k: keyof Form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const ready = form.cost !== "" && form.sell !== "";

  async function analyze() {
    setError(null);
    setBusy(true);
    try {
      const { data } = await pricingApi.analyze({
        cost: parseFloat(form.cost),
        sell: parseFloat(form.sell),
        delivery: parseFloat(form.delivery) || 0,
        packaging: parseFloat(form.packaging) || 0,
      });
      setResult(data);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Analysis failed.");
    } finally {
      setBusy(false);
    }
  }

  const marginColor =
    result == null ? "var(--text)"
    : result.margin_pct >= 25 ? "var(--success)"
    : result.margin_pct >= 10 ? "#f59e0b"
    : "var(--danger)";

  return (
    <PageShell title="Pricing Advisor" subtitle="Enter your costs — the system calculates your margin and AI explains it in plain language">
      <div style={styles.card}>
        <div style={styles.grid}>
          {(
            [
              ["cost",      "Cost Price ($)"],
              ["sell",      "Selling Price ($)"],
              ["delivery",  "Delivery Cost ($)"],
              ["packaging", "Packaging Cost ($)"],
            ] as [keyof Form, string][]
          ).map(([k, label]) => (
            <div key={k}>
              <label style={styles.label}>{label}</label>
              <input style={styles.input} type="number" min="0" step="0.01" placeholder="0.00" value={form[k]} onChange={set(k)} />
            </div>
          ))}
        </div>
        <button style={{ ...styles.btn, opacity: ready && !busy ? 1 : 0.5 }} disabled={!ready || busy} onClick={analyze}>
          {busy ? "Analyzing…" : "Analyze with AI"}
        </button>
      </div>

      {error && <div style={styles.errorBanner}>⚠ {error}</div>}

      {result ? (
        <>
          <div style={styles.metrics}>
            <Metric label="Total Cost" value={`$${result.total_cost.toFixed(2)}`} />
            <Metric label="Profit / Unit" value={`$${result.profit.toFixed(2)}`} color={result.profit >= 0 ? "var(--success)" : "var(--danger)"} />
            <Metric label="Margin" value={`${result.margin_pct.toFixed(1)}%`} color={marginColor} />
            <Metric label="Price for 25% Margin" value={`$${result.sell_for_25pct.toFixed(2)}`} />
          </div>

          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>🤖 AI Explanation</h3>
            <div style={styles.explainCard}>{result.explanation}</div>
          </div>
        </>
      ) : (
        <div style={styles.emptyState}>
          Fill in the costs above and click Analyze to see your profit margin and AI recommendations here.
        </div>
      )}
    </PageShell>
  );
}

function Metric({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={styles.metricCard}>
      <span style={styles.metricLabel}>{label}</span>
      <span style={{ ...styles.metricValue, color: color ?? "var(--text)" }}>{value}</span>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 24, marginBottom: 24 },
  grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 },
  label: { display: "block", fontSize: 13, color: "var(--text-muted)", marginBottom: 6 },
  input: { width: "100%", background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: 6, padding: "10px 12px", color: "var(--text)" },
  btn: { background: "var(--accent)", color: "#fff", border: "none", borderRadius: 6, padding: "10px 24px", fontWeight: 600, fontSize: 14 },
  errorBanner: { background: "#ef444418", border: "1px solid #ef444444", borderRadius: "var(--radius)", padding: "12px 16px", marginBottom: 20, color: "var(--danger)", fontSize: 13 },
  metrics: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 24 },
  metricCard: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "16px 18px", display: "flex", flexDirection: "column", gap: 6 },
  metricLabel: { color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.5px" },
  metricValue: { fontWeight: 700, fontSize: 22 },
  section: { marginBottom: 28 },
  sectionTitle: { fontWeight: 600, marginBottom: 12, fontSize: 15 },
  explainCard: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "18px 20px", fontSize: 14, lineHeight: 1.6 },
  emptyState: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 24, color: "var(--text-muted)", textAlign: "center" },
};
