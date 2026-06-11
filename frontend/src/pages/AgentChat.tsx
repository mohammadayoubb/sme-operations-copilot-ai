import { useEffect, useRef, useState } from "react";
import PageShell from "../components/PageShell";

const BASE = (import.meta.env.VITE_API_URL as string) ?? "";

interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
}

interface ToolCall {
  tool: string;
  args: Record<string, unknown>;
  result: Record<string, unknown>;
}

interface DisplayMessage {
  role: "user" | "assistant";
  content: string;
  tool_calls?: ToolCall[];
  streaming?: boolean;
}

const EXAMPLE_PROMPTS = [
  "What should I reorder this week?",
  "How are my sales compared to last week?",
  "Which products are running low?",
  "Record an order: 3 black hoodies size L, delivery to Hamra, cash on delivery",
  "Show me the price history for Nutella",
  "Give me a summary of recent orders",
];

const TOOL_ICONS: Record<string, string> = {
  check_stock: "📦",
  get_reorder_alerts: "🔮",
  get_sales_summary: "📈",
  get_latest_report: "📊",
  list_recent_orders: "🛍",
  get_price_history: "💰",
  create_order: "✅",
};

function ToolCallBadge({ tc, pending }: { tc: ToolCall; pending?: boolean }) {
  const [open, setOpen] = useState(false);
  const icon = TOOL_ICONS[tc.tool] ?? "🔧";
  const label = tc.tool.replace(/_/g, " ");

  return (
    <div style={styles.toolBadge}>
      <button style={styles.toolHeader} onClick={() => !pending && setOpen((o) => !o)}>
        <span style={styles.toolIcon}>{pending ? "⏳" : icon}</span>
        <span style={{ ...styles.toolLabel, color: pending ? "var(--text-muted)" : undefined }}>
          {label}{pending ? "…" : ""}
        </span>
        {!pending && <span style={styles.toolChevron}>{open ? "▲" : "▼"}</span>}
      </button>
      {open && !pending && (
        <pre style={styles.toolJson}>{JSON.stringify(tc.result, null, 2)}</pre>
      )}
    </div>
  );
}

function MessageBubble({ msg }: { msg: DisplayMessage }) {
  const isUser = msg.role === "user";
  return (
    <div style={{ ...styles.bubble, ...(isUser ? styles.bubbleUser : styles.bubbleAssistant) }}>
      {!isUser && msg.tool_calls && msg.tool_calls.length > 0 && (
        <div style={styles.toolCalls}>
          {msg.tool_calls.map((tc, i) => (
            <ToolCallBadge key={i} tc={tc} pending={!tc.result || Object.keys(tc.result).length === 0} />
          ))}
        </div>
      )}
      {msg.content ? (
        <p style={styles.bubbleText}>{msg.content}{msg.streaming ? <span style={styles.cursor}>▌</span> : null}</p>
      ) : msg.streaming ? (
        <p style={{ ...styles.bubbleText, color: "var(--text-muted)" }}>
          <span style={styles.cursor}>▌</span>
        </p>
      ) : null}
    </div>
  );
}

export default function AgentChat() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [history, setHistory] = useState<HistoryMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || busy) return;

    setInput("");
    setError(null);
    setBusy(true);

    const userMsg: DisplayMessage = { role: "user", content: msg };
    const placeholder: DisplayMessage = { role: "assistant", content: "", tool_calls: [], streaming: true };
    setMessages((prev) => [...prev, userMsg, placeholder]);

    // Local accumulators — avoid stale closure issues by mutating these refs
    const toolsAccum: ToolCall[] = [];
    let responseText = "";

    const updateLast = () => {
      setMessages((prev) => {
        const copy = [...prev];
        copy[copy.length - 1] = {
          role: "assistant",
          content: responseText,
          tool_calls: toolsAccum.map((t) => ({ ...t })),
          streaming: true,
        };
        return copy;
      });
    };

    try {
      const token = localStorage.getItem("soukpilot_token");
      const res = await fetch(`${BASE}/api/agent/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ message: msg, history }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        throw new Error(err.detail ?? `HTTP ${res.status}`);
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop() ?? "";

        for (const part of parts) {
          if (!part.startsWith("data: ")) continue;
          let event: Record<string, unknown>;
          try { event = JSON.parse(part.slice(6)); } catch { continue; }

          if (event.type === "tool_start") {
            toolsAccum.push({ tool: event.tool as string, args: (event.args as Record<string, unknown>) ?? {}, result: {} });
            updateLast();
          } else if (event.type === "tool_result") {
            const last = toolsAccum.findLastIndex((tc) => tc.tool === (event.tool as string));
            if (last >= 0) toolsAccum[last] = { ...toolsAccum[last], result: (event.result as Record<string, unknown>) ?? {} };
            updateLast();
          } else if (event.type === "text") {
            responseText += event.text as string;
            updateLast();
          } else if (event.type === "done") {
            setHistory((h) => [...h, { role: "user", content: msg }, { role: "assistant", content: responseText }]);
            setMessages((prev) => {
              const copy = [...prev];
              copy[copy.length - 1] = { role: "assistant", content: responseText, tool_calls: toolsAccum.map((t) => ({ ...t })), streaming: false };
              return copy;
            });
          } else if (event.type === "error") {
            throw new Error(event.error as string);
          }
        }
      }
    } catch (e: any) {
      setError(e?.message ?? "Something went wrong.");
      setMessages((prev) => prev.slice(0, -2));
    } finally {
      setBusy(false);
    }
  }

  function clear() {
    setMessages([]);
    setHistory([]);
    setError(null);
  }

  return (
    <PageShell
      title="AI Agent"
      subtitle="Ask anything about your business — the agent looks up live data, calls the right tools, and answers in plain language"
    >
      {messages.length === 0 && !busy && (
        <div style={styles.emptyState}>
          <div style={styles.emptyIcon}>🤖</div>
          <p style={styles.emptyTitle}>Ask me anything about your business</p>
          <p style={styles.emptySub}>
            I have access to your stock levels, sales, orders, invoices, forecasts, and reports.
            I can also create orders for you.
          </p>
          <div style={styles.examples}>
            {EXAMPLE_PROMPTS.map((p) => (
              <button key={p} style={styles.exampleBtn} onClick={() => send(p)}>
                {p}
              </button>
            ))}
          </div>
        </div>
      )}

      {messages.length > 0 && (
        <div style={styles.chat}>
          {messages.map((m, i) => (
            <MessageBubble key={i} msg={m} />
          ))}
          <div ref={bottomRef} />
        </div>
      )}

      {error && <div style={styles.errorBanner}>⚠ {error}</div>}

      <div style={styles.inputRow}>
        <input
          style={styles.input}
          type="text"
          placeholder="Ask about stock, sales, orders, or say 'record an order for…'"
          value={input}
          disabled={busy}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
        />
        <button
          style={{ ...styles.sendBtn, opacity: input.trim() && !busy ? 1 : 0.5 }}
          disabled={!input.trim() || busy}
          onClick={() => send()}
        >
          {busy ? "…" : "Send"}
        </button>
        {messages.length > 0 && (
          <button style={styles.clearBtn} onClick={clear} disabled={busy}>
            Clear
          </button>
        )}
      </div>
    </PageShell>
  );
}

const styles: Record<string, React.CSSProperties> = {
  emptyState: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "40px 32px", textAlign: "center", marginBottom: 24 },
  emptyIcon: { fontSize: 48, marginBottom: 12 },
  emptyTitle: { fontWeight: 700, fontSize: 16, marginBottom: 8 },
  emptySub: { color: "var(--text-muted)", fontSize: 13, maxWidth: 480, margin: "0 auto 24px", lineHeight: 1.6 },
  examples: { display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center" },
  exampleBtn: { background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: 100, padding: "7px 16px", color: "var(--text-muted)", fontSize: 12, cursor: "pointer" },
  chat: { display: "flex", flexDirection: "column", gap: 16, marginBottom: 20, maxHeight: 520, overflowY: "auto", paddingRight: 4 },
  bubble: { maxWidth: "82%", borderRadius: "var(--radius)", padding: "14px 18px" },
  bubbleUser: { alignSelf: "flex-end", background: "var(--accent)", color: "#fff" },
  bubbleAssistant: { alignSelf: "flex-start", background: "var(--surface)", border: "1px solid var(--border)" },
  bubbleText: { fontSize: 14, lineHeight: 1.6, margin: 0, whiteSpace: "pre-wrap" },
  cursor: { display: "inline-block", animation: "blink 1s step-end infinite", marginLeft: 1 },
  toolCalls: { display: "flex", flexDirection: "column", gap: 6, marginBottom: 10 },
  toolBadge: { background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: 6, overflow: "hidden" },
  toolHeader: { display: "flex", alignItems: "center", gap: 8, width: "100%", padding: "7px 12px", background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", fontSize: 12, textAlign: "left" },
  toolIcon: { fontSize: 14 },
  toolLabel: { flex: 1, fontWeight: 600, textTransform: "lowercase" },
  toolChevron: { fontSize: 10 },
  toolJson: { padding: "10px 14px", borderTop: "1px solid var(--border)", fontSize: 11.5, overflowX: "auto", margin: 0, color: "var(--text-muted)" },
  errorBanner: { background: "#ef444418", border: "1px solid #ef444444", borderRadius: "var(--radius)", padding: "12px 16px", marginBottom: 16, color: "var(--danger)", fontSize: 13 },
  inputRow: { display: "flex", gap: 10, alignItems: "center" },
  input: { flex: 1, background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: 6, padding: "11px 14px", color: "var(--text)", fontSize: 14 },
  sendBtn: { background: "var(--accent)", color: "#fff", border: "none", borderRadius: 6, padding: "11px 22px", fontWeight: 600, fontSize: 14 },
  clearBtn: { background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: 6, padding: "11px 16px", color: "var(--text-muted)", fontSize: 13, cursor: "pointer" },
};
