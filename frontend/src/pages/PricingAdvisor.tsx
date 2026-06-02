import { useState } from "react";
import PageShell from "../components/PageShell";

interface Form { cost: string; sell: string; delivery: string; packaging: string; }

export default function PricingAdvisor() {
  const [form, setForm] = useState<Form>({ cost: "", sell: "", delivery: "", packaging: "" });

  const set = (k: keyof Form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const ready = Object.values(form).every((v) => v !== "");

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
        <button style={{ ...styles.btn, opacity: ready ? 1 : 0.5 }} disabled={!ready}>
          Analyze with AI
        </button>
      </div>

      <div style={styles.emptyState}>
        Fill in the costs above and click Analyze to see your profit margin and AI recommendations here.
      </div>
    </PageShell>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 24, marginBottom: 24 },
  grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 },
  label: { display: "block", fontSize: 13, color: "var(--text-muted)", marginBottom: 6 },
  input: { width: "100%", background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: 6, padding: "10px 12px", color: "var(--text)" },
  btn: { background: "var(--accent)", color: "#fff", border: "none", borderRadius: 6, padding: "10px 24px", fontWeight: 600, fontSize: 14 },
  emptyState: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 24, color: "var(--text-muted)", textAlign: "center" },
};
