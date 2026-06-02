import { useState } from "react";
import PageShell from "../components/PageShell";

const EXAMPLE_QUESTIONS = [
  "Which supplier increased prices the most this month?",
  "Which product made the most profit this week?",
  "What should I reorder before the weekend?",
  "Why did my profit drop compared to last week?",
];

export default function BusinessQA() {
  const [question, setQuestion] = useState("");

  return (
    <PageShell title="Business Q&A" subtitle="Ask any question about your business data — answers are grounded in your actual invoices, orders, and sales">
      <div style={styles.card}>
        <div style={styles.examples}>
          {EXAMPLE_QUESTIONS.map((q) => (
            <button key={q} style={styles.exampleBtn} onClick={() => setQuestion(q)}>
              {q}
            </button>
          ))}
        </div>
        <div style={styles.inputRow}>
          <input
            style={styles.input}
            type="text"
            placeholder="Ask a question about your business..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <button style={{ ...styles.btn, opacity: question.trim() ? 1 : 0.5 }} disabled={!question.trim()}>
            Ask
          </button>
        </div>
      </div>

      <div style={styles.emptyState}>
        Ask a question above to see a grounded AI answer with source references here.
      </div>
    </PageShell>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 24, marginBottom: 24 },
  examples: { display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 },
  exampleBtn: { background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: 100, padding: "5px 14px", color: "var(--text-muted)", fontSize: 12, cursor: "pointer" },
  inputRow: { display: "flex", gap: 10 },
  input: { flex: 1, background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: 6, padding: "10px 14px", color: "var(--text)", fontSize: 14 },
  btn: { background: "var(--accent)", color: "#fff", border: "none", borderRadius: 6, padding: "10px 20px", fontWeight: 600, fontSize: 14, whiteSpace: "nowrap" },
  emptyState: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 24, color: "var(--text-muted)", textAlign: "center" },
};
