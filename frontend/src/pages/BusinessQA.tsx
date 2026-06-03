import { useState } from "react";
import PageShell from "../components/PageShell";
import { qaApi } from "../services/api";

const EXAMPLE_QUESTIONS = [
  "Which supplier increased prices the most this month?",
  "Which product made the most profit this week?",
  "What should I reorder before the weekend?",
  "Why did my profit drop compared to last week?",
];

interface Source {
  source_type: string | null;
  source_id: number | null;
  content: string;
  score: number | null;
}

interface RetrievalStats {
  candidates?: number;
  reranked?: boolean;
  returned?: number;
  parents_shown?: number;
}

interface Answer {
  answer: string;
  grounded: boolean;
  sources: Source[];
  retrieval_stats: RetrievalStats;
}

export default function BusinessQA() {
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [result, setResult] = useState<Answer | null>(null);

  async function ask(q?: string) {
    const query = (q ?? question).trim();
    if (!query) return;
    setError(null);
    setNotice(null);
    setResult(null);
    setBusy(true);
    try {
      const { data } = await qaApi.ask(query);
      setResult(data);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Could not answer the question.");
    } finally {
      setBusy(false);
    }
  }

  async function reindex() {
    setError(null);
    setNotice(null);
    setIndexing(true);
    try {
      const { data } = await qaApi.index();
      setNotice(`Indexed ${data.documents_indexed} records (${data.chunks_indexed} chunks).`);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Indexing failed.");
    } finally {
      setIndexing(false);
    }
  }

  const stats = result?.retrieval_stats;
  const statsLine = stats && stats.candidates != null
    ? `${stats.candidates} candidates · BM25 reranked · ${stats.parents_shown ?? stats.returned} sources`
    : null;

  return (
    <PageShell title="Business Q&A" subtitle="Ask any question about your business data — answers are grounded in your actual invoices, orders, and sales">
      <div style={styles.card}>
        <div style={styles.toolbar}>
          <div style={styles.examples}>
            {EXAMPLE_QUESTIONS.map((q) => (
              <button key={q} style={styles.exampleBtn} onClick={() => { setQuestion(q); ask(q); }}>
                {q}
              </button>
            ))}
          </div>
          <button style={styles.indexBtn} disabled={indexing} onClick={reindex} title="Rebuild the index from current data">
            {indexing ? "Indexing…" : "↻ Reindex data"}
          </button>
        </div>
        <div style={styles.inputRow}>
          <input
            style={styles.input}
            type="text"
            placeholder="Ask a question about your business..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask()}
          />
          <button style={{ ...styles.btn, opacity: question.trim() && !busy ? 1 : 0.5 }} disabled={!question.trim() || busy} onClick={() => ask()}>
            {busy ? "Thinking…" : "Ask"}
          </button>
        </div>
      </div>

      {notice && <div style={styles.noticeBanner}>✓ {notice}</div>}
      {error && <div style={styles.errorBanner}>⚠ {error}</div>}

      {result ? (
        <div style={styles.section}>
          <div style={styles.answerCard}>
            <div style={styles.answerHeader}>
              <span style={styles.answerTitle}>Answer</span>
              <div style={styles.badges}>
                {result.retrieval_stats?.reranked && (
                  <span style={styles.hybridBadge}>HYBRID</span>
                )}
                <span style={{ ...styles.groundBadge, background: result.grounded ? "#22c55e22" : "#f59e0b22", color: result.grounded ? "#22c55e" : "#f59e0b" }}>
                  {result.grounded ? "GROUNDED" : "NO DATA"}
                </span>
              </div>
            </div>
            {statsLine && (
              <p style={styles.statsLine}>{statsLine}</p>
            )}
            <p style={styles.answerText}>{result.answer}</p>
          </div>

          {result.sources.length > 0 && (
            <>
              <h3 style={styles.sourcesTitle}>Sources ({result.sources.length})</h3>
              <div style={styles.sources}>
                {result.sources.map((s, i) => (
                  <div key={i} style={styles.sourceCard}>
                    <div style={styles.sourceMeta}>
                      <span style={styles.sourceTag}>{s.source_type ?? "record"}{s.source_id != null ? ` #${s.source_id}` : ""}</span>
                      {s.score != null && <span style={styles.sourceScore}>similarity {(s.score * 100).toFixed(0)}%</span>}
                    </div>
                    <p style={styles.sourceContent}>{s.content}</p>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      ) : (
        <div style={styles.emptyState}>
          Ask a question above to see a grounded AI answer with source references here.
          <br />
          <span style={styles.hint}>Tip: click "Reindex data" first if you've added new invoices or orders.</span>
        </div>
      )}
    </PageShell>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 24, marginBottom: 24 },
  toolbar: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, marginBottom: 16 },
  examples: { display: "flex", flexWrap: "wrap", gap: 8 },
  exampleBtn: { background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: 100, padding: "5px 14px", color: "var(--text-muted)", fontSize: 12, cursor: "pointer" },
  indexBtn: { background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: 6, padding: "6px 12px", color: "var(--text-muted)", fontSize: 12, cursor: "pointer", whiteSpace: "nowrap" },
  inputRow: { display: "flex", gap: 10 },
  input: { flex: 1, background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: 6, padding: "10px 14px", color: "var(--text)", fontSize: 14 },
  btn: { background: "var(--accent)", color: "#fff", border: "none", borderRadius: 6, padding: "10px 20px", fontWeight: 600, fontSize: 14, whiteSpace: "nowrap" },
  noticeBanner: { background: "#22c55e18", border: "1px solid #22c55e44", borderRadius: "var(--radius)", padding: "12px 16px", marginBottom: 20, color: "#22c55e", fontSize: 13 },
  errorBanner: { background: "#ef444418", border: "1px solid #ef444444", borderRadius: "var(--radius)", padding: "12px 16px", marginBottom: 20, color: "var(--danger)", fontSize: 13 },
  section: { marginBottom: 28 },
  answerCard: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "18px 20px", marginBottom: 20 },
  answerHeader: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 },
  answerTitle: { fontWeight: 700, fontSize: 14 },
  badges: { display: "flex", gap: 6, alignItems: "center" },
  hybridBadge: { fontSize: 10, fontWeight: 700, padding: "3px 8px", borderRadius: 100, background: "#6366f122", color: "#818cf8" },
  groundBadge: { fontSize: 10, fontWeight: 700, padding: "3px 8px", borderRadius: 100 },
  statsLine: { fontSize: 11, color: "var(--text-muted)", margin: "0 0 10px", letterSpacing: "0.2px" },
  answerText: { fontSize: 14, lineHeight: 1.6 },
  sourcesTitle: { fontWeight: 600, marginBottom: 12, fontSize: 14 },
  sources: { display: "flex", flexDirection: "column", gap: 10 },
  sourceCard: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "12px 16px" },
  sourceMeta: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 },
  sourceTag: { fontSize: 11, fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.5px" },
  sourceScore: { fontSize: 11, color: "var(--text-muted)" },
  sourceContent: { fontSize: 13, color: "var(--text-muted)", lineHeight: 1.5 },
  emptyState: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 24, color: "var(--text-muted)", textAlign: "center", lineHeight: 1.8 },
  hint: { fontSize: 12 },
};
