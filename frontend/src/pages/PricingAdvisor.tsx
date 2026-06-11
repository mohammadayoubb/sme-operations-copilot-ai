import { useEffect, useState } from "react";
import PageShell from "../components/PageShell";
import { pricingApi } from "../services/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ProductOption {
  id: number;
  name: string;
  current_stock: number;
  latest_cost: number | null;
  cost_change_pct: number | null;
  avg_daily_sales: number | null;
  velocity: string;
}

interface Scenario {
  label: string;
  target_margin_pct: number;
  required_price: number;
  profit: number;
}

interface CostTrend {
  prev_cost: number;
  current_cost: number;
  change_pct: number;
  direction: "up" | "down" | "flat";
}

interface Result {
  total_cost: number;
  profit: number;
  margin_pct: number;
  sell_for_25pct: number;
  scenarios: Scenario[];
  velocity: string;
  velocity_avg_daily: number | null;
  cost_trend: CostTrend | null;
  assessment: string;
  recommendation: string;
  risk: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const VELOCITY_COLORS: Record<string, string> = {
  fast:    "#34d399",
  medium:  "#fb923c",
  slow:    "#f87171",
  unknown: "var(--text-muted)",
};

const VELOCITY_ICONS: Record<string, string> = {
  fast: "🚀", medium: "📦", slow: "🐢", unknown: "—",
};

function marginColor(pct: number) {
  if (pct >= 25) return "var(--success)";
  if (pct >= 10) return "#f59e0b";
  return "var(--danger)";
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Metric({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={S.metricCard}>
      <span style={S.metricLabel}>{label}</span>
      <span style={{ ...S.metricValue, color: color ?? "var(--text)" }}>{value}</span>
    </div>
  );
}

function ScenarioTable({ scenarios, currentSell }: { scenarios: Scenario[]; currentSell: number }) {
  return (
    <div style={S.tableWrap}>
      <table style={S.table}>
        <thead>
          <tr>
            {["Target", "Required Price", "Profit / Unit", "vs. Current"].map(h => (
              <th key={h} style={S.th}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {scenarios.map((s) => {
            const isCurrent = Math.abs(s.required_price - currentSell) < 0.01;
            const diff = s.required_price - currentSell;
            return (
              <tr key={s.label} style={{ ...S.tr, ...(isCurrent ? S.trHighlight : {}) }}>
                <td style={S.td}>
                  <span style={{ fontWeight: 600 }}>{s.label}</span>
                  {isCurrent && (
                    <span style={S.currentBadge}>current</span>
                  )}
                </td>
                <td style={{ ...S.td, fontWeight: 600 }}>${s.required_price.toFixed(2)}</td>
                <td style={{ ...S.td, color: s.profit >= 0 ? "var(--success)" : "var(--danger)" }}>
                  ${s.profit.toFixed(2)}
                </td>
                <td style={{ ...S.td, color: diff > 0 ? "#fb923c" : diff < 0 ? "var(--success)" : "var(--text-muted)" }}>
                  {diff === 0 ? "—" : `${diff > 0 ? "+" : ""}$${diff.toFixed(2)}`}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function StrategyCard({ icon, title, text, accent }: { icon: string; title: string; text: string; accent: string }) {
  if (!text) return null;
  return (
    <div style={{ ...S.strategyCard, borderLeft: `3px solid ${accent}` }}>
      <p style={{ ...S.strategyTitle, color: accent }}>{icon} {title}</p>
      <p style={S.strategyText}>{text}</p>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function PricingAdvisor() {
  const [products, setProducts] = useState<ProductOption[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const [form, setForm] = useState({ cost: "", sell: "", delivery: "", packaging: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Result | null>(null);

  // Load product list on mount
  useEffect(() => {
    pricingApi.products().then(({ data }) => setProducts(data)).catch(() => {});
  }, []);

  // Auto-fill cost when product is selected
  function handleProductChange(idStr: string) {
    if (idStr === "") {
      setSelectedId(null);
      return;
    }
    const id = parseInt(idStr);
    setSelectedId(id);
    const p = products.find((x) => x.id === id);
    if (p?.latest_cost != null) {
      setForm((f) => ({ ...f, cost: String(p.latest_cost) }));
    }
  }

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const ready = form.cost !== "" && form.sell !== "";

  async function analyze() {
    setError(null);
    setBusy(true);
    try {
      const selected = products.find((p) => p.id === selectedId);
      const { data } = await pricingApi.analyze({
        cost:       parseFloat(form.cost),
        sell:       parseFloat(form.sell),
        delivery:   parseFloat(form.delivery) || 0,
        packaging:  parseFloat(form.packaging) || 0,
        product_id:   selectedId ?? null,
        product_name: selected?.name ?? null,
      });
      setResult(data);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Analysis failed.");
    } finally {
      setBusy(false);
    }
  }

  const selectedProduct = products.find((p) => p.id === selectedId);

  return (
    <PageShell
      title="Pricing Advisor"
      subtitle="Select a product or enter costs manually — AI builds a full pricing strategy from your live data"
    >
      {/* ── Input card ── */}
      <div style={S.card}>

        {/* Product selector */}
        <div style={S.field}>
          <label style={S.label}>Product (optional)</label>
          <select
            style={S.select}
            value={selectedId ?? ""}
            onChange={(e) => handleProductChange(e.target.value)}
          >
            <option value="">Enter manually</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
                {p.latest_cost != null ? ` — cost $${p.latest_cost.toFixed(2)}` : ""}
                {p.cost_change_pct != null && p.cost_change_pct !== 0
                  ? ` (${p.cost_change_pct > 0 ? "↑" : "↓"}${Math.abs(p.cost_change_pct).toFixed(1)}%)`
                  : ""}
              </option>
            ))}
          </select>
        </div>

        {/* If a product is selected, show a context strip */}
        {selectedProduct && (
          <div style={S.contextStrip}>
            <span style={{ color: VELOCITY_COLORS[selectedProduct.velocity] }}>
              {VELOCITY_ICONS[selectedProduct.velocity]} {selectedProduct.velocity} mover
              {selectedProduct.avg_daily_sales != null
                ? ` · ${selectedProduct.avg_daily_sales} units/day`
                : ""}
            </span>
            <span style={{ color: "var(--text-muted)" }}>·</span>
            <span style={{ color: "var(--text-muted)" }}>
              Stock: {selectedProduct.current_stock} units
            </span>
            {selectedProduct.cost_change_pct != null && selectedProduct.cost_change_pct !== 0 && (
              <>
                <span style={{ color: "var(--text-muted)" }}>·</span>
                <span style={{ color: selectedProduct.cost_change_pct > 0 ? "var(--danger)" : "var(--success)" }}>
                  Cost {selectedProduct.cost_change_pct > 0 ? "↑" : "↓"}
                  {Math.abs(selectedProduct.cost_change_pct).toFixed(1)}% since last invoice
                </span>
              </>
            )}
          </div>
        )}

        {/* Number inputs */}
        <div style={S.grid}>
          {([
            ["cost",      "Cost Price ($)",      "Auto-filled from latest invoice"],
            ["sell",      "Selling Price ($)",   "What you charge customers"],
            ["delivery",  "Delivery Cost ($)",   "Per unit"],
            ["packaging", "Packaging Cost ($)",  "Per unit"],
          ] as [keyof typeof form, string, string][]).map(([k, lbl, hint]) => (
            <div key={k}>
              <label style={S.label}>
                {lbl}
                <span style={S.hint}>{hint}</span>
              </label>
              <input
                style={S.input}
                type="number"
                min="0"
                step="0.01"
                placeholder="0.00"
                value={form[k]}
                onChange={set(k)}
              />
            </div>
          ))}
        </div>

        <button
          style={{ ...S.btn, opacity: ready && !busy ? 1 : 0.5 }}
          disabled={!ready || busy}
          onClick={analyze}
        >
          {busy ? "Analyzing…" : "Analyze with AI"}
        </button>
      </div>

      {error && <div style={S.errorBanner}>⚠ {error}</div>}

      {result && (
        <>
          {/* ── Core metrics ── */}
          <div style={S.metrics}>
            <Metric label="Total Cost / Unit" value={`$${result.total_cost.toFixed(2)}`} />
            <Metric
              label="Profit / Unit"
              value={`$${result.profit.toFixed(2)}`}
              color={result.profit >= 0 ? "var(--success)" : "var(--danger)"}
            />
            <Metric
              label="Gross Margin"
              value={`${result.margin_pct.toFixed(1)}%`}
              color={marginColor(result.margin_pct)}
            />
            <Metric label="Price for 25% Margin" value={`$${result.sell_for_25pct.toFixed(2)}`} />
          </div>

          {/* ── Context badges ── */}
          <div style={S.badgeRow}>
            <div style={{ ...S.badge, borderColor: VELOCITY_COLORS[result.velocity] }}>
              <span style={{ color: VELOCITY_COLORS[result.velocity] }}>
                {VELOCITY_ICONS[result.velocity]} {result.velocity} mover
              </span>
              {result.velocity_avg_daily != null && (
                <span style={S.badgeSub}>{result.velocity_avg_daily} units/day</span>
              )}
            </div>

            {result.cost_trend && (
              <div style={{
                ...S.badge,
                borderColor: result.cost_trend.direction === "up"
                  ? "var(--danger)" : result.cost_trend.direction === "down"
                  ? "var(--success)" : "var(--border)",
              }}>
                <span style={{
                  color: result.cost_trend.direction === "up"
                    ? "var(--danger)" : result.cost_trend.direction === "down"
                    ? "var(--success)" : "var(--text-muted)",
                }}>
                  {result.cost_trend.direction === "up" ? "↑" : result.cost_trend.direction === "down" ? "↓" : "→"}
                  {" "}Supplier cost {result.cost_trend.direction}{" "}
                  {Math.abs(result.cost_trend.change_pct).toFixed(1)}%
                </span>
                <span style={S.badgeSub}>
                  ${result.cost_trend.prev_cost.toFixed(2)} → ${result.cost_trend.current_cost.toFixed(2)}
                </span>
              </div>
            )}
          </div>

          {/* ── Scenario table ── */}
          <div style={S.section}>
            <h3 style={S.sectionTitle}>📊 Pricing Scenarios</h3>
            <ScenarioTable scenarios={result.scenarios} currentSell={parseFloat(form.sell)} />
          </div>

          {/* ── AI strategy ── */}
          <div style={S.section}>
            <h3 style={S.sectionTitle}>🤖 AI Strategy</h3>
            <div style={S.strategyGrid}>
              <StrategyCard
                icon="📍"
                title="Current Position"
                text={result.assessment}
                accent="#818cf8"
              />
              <StrategyCard
                icon="🎯"
                title="Recommendation"
                text={result.recommendation}
                accent="#34d399"
              />
              <StrategyCard
                icon="⚠️"
                title="Risk to Watch"
                text={result.risk}
                accent="#fb923c"
              />
            </div>
          </div>
        </>
      )}

      {!result && (
        <div style={S.emptyState}>
          Select a product or enter costs manually, then click Analyze to get your margin breakdown, scenario table, and AI strategy recommendation.
        </div>
      )}
    </PageShell>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────────

const S: Record<string, React.CSSProperties> = {
  card: {
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    padding: 24,
    marginBottom: 24,
  },
  field: { marginBottom: 16 },
  label: {
    display: "flex",
    flexDirection: "column",
    gap: 2,
    fontSize: 13,
    color: "var(--text-muted)",
    marginBottom: 6,
    fontWeight: 500,
  },
  hint: { fontSize: 11, color: "var(--text-muted)", fontWeight: 400 },
  select: {
    width: "100%",
    background: "#1a1d2e",
    border: "1px solid rgba(255,255,255,0.18)",
    borderRadius: 6,
    padding: "10px 12px",
    color: "var(--text)",
    fontSize: 14,
  },
  contextStrip: {
    display: "flex",
    gap: 10,
    alignItems: "center",
    flexWrap: "wrap" as const,
    background: "var(--surface2)",
    borderRadius: 6,
    padding: "8px 12px",
    fontSize: 12,
    marginBottom: 16,
  },
  grid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 },
  input: {
    width: "100%",
    background: "#1a1d2e",
    border: "1px solid rgba(255,255,255,0.18)",
    borderRadius: 6,
    padding: "10px 12px",
    color: "var(--text)",
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
  errorBanner: {
    background: "#ef444418",
    border: "1px solid #ef444444",
    borderRadius: "var(--radius)",
    padding: "12px 16px",
    marginBottom: 20,
    color: "var(--danger)",
    fontSize: 13,
  },
  metrics: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: 14,
    marginBottom: 16,
  },
  metricCard: {
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    padding: "16px 18px",
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  metricLabel: {
    color: "var(--text-muted)",
    fontSize: 11,
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
  },
  metricValue: { fontWeight: 700, fontSize: 22 },
  badgeRow: { display: "flex", gap: 10, flexWrap: "wrap" as const, marginBottom: 24 },
  badge: {
    display: "flex",
    flexDirection: "column" as const,
    gap: 2,
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: 8,
    padding: "10px 14px",
    fontSize: 13,
    fontWeight: 600,
    minWidth: 160,
  },
  badgeSub: { fontSize: 11, color: "var(--text-muted)", fontWeight: 400 },
  section: { marginBottom: 28 },
  sectionTitle: { fontWeight: 600, marginBottom: 12, fontSize: 15, marginTop: 0 },
  tableWrap: {
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    overflow: "hidden",
  },
  table: { width: "100%", borderCollapse: "collapse" as const },
  th: {
    textAlign: "left" as const,
    padding: "10px 16px",
    color: "var(--text-muted)",
    fontSize: 11,
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
    fontWeight: 600,
    borderBottom: "1px solid var(--border)",
  },
  tr: { borderTop: "1px solid var(--border)" },
  trHighlight: { background: "rgba(129,140,248,0.07)" },
  td: { padding: "11px 16px", fontSize: 14 },
  currentBadge: {
    marginLeft: 8,
    fontSize: 10,
    fontWeight: 700,
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
    background: "rgba(129,140,248,0.15)",
    color: "var(--accent)",
    borderRadius: 4,
    padding: "1px 6px",
  },
  strategyGrid: { display: "flex", flexDirection: "column" as const, gap: 12 },
  strategyCard: {
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    padding: "14px 18px",
  },
  strategyTitle: { fontWeight: 700, fontSize: 12, textTransform: "uppercase" as const, letterSpacing: "0.5px", marginBottom: 6, marginTop: 0 },
  strategyText: { fontSize: 14, lineHeight: 1.7, margin: 0, color: "var(--text)" },
  emptyState: {
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    padding: 24,
    color: "var(--text-muted)",
    textAlign: "center" as const,
    fontSize: 14,
    lineHeight: 1.6,
  },
};
