/**
 * Self-contained embeddable widget.
 *
 * Two states managed entirely inside the iframe:
 *   collapsed → 64×64 iframe showing only a floating chat button
 *   expanded  → 380×560 iframe showing the full chat panel
 *
 * On each state change a postMessage is sent to the parent page so the
 * snippet can resize the iframe.  Works identically when visited directly
 * (standalone preview) without needing any parent cooperation.
 */
import { useEffect, useRef, useState } from "react";
import LogoIcon from "../components/LogoIcon";

const BASE = ((import.meta.env.VITE_API_URL as string) ?? "").replace(/\/+$/, "");

const COLLAPSED = { w: 64,  h: 64  };
const EXPANDED  = { w: 380, h: 560 };

interface HistoryMessage { role: "user" | "assistant"; content: string; }
interface ToolCall { tool: string; args: Record<string, unknown>; result: Record<string, unknown>; }
interface DisplayMessage {
  role: "user" | "assistant";
  content: string;
  tool_calls?: ToolCall[];
  streaming?: boolean;
}

const TOOL_ICONS: Record<string, string> = {
  check_stock: "📦", get_reorder_alerts: "🔮", get_sales_summary: "📈",
  get_latest_report: "📊", list_recent_orders: "🛍", get_price_history: "💰", create_order: "✅",
};

const EXAMPLES = ["What should I reorder?", "How are sales this week?", "Which items are running low?"];

// ── Sub-components ───────────────────────────────────────────────────────────

function ToolBadge({ tc, pending }: { tc: ToolCall; pending?: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={S.toolBadge}>
      <button style={S.toolHeader} onClick={() => !pending && setOpen(o => !o)}>
        <span>{pending ? "⏳" : (TOOL_ICONS[tc.tool] ?? "🔧")}</span>
        <span style={{ flex: 1, fontSize: 11, color: "rgba(255,255,255,0.5)", fontWeight: 600 }}>
          {tc.tool.replace(/_/g, " ")}{pending ? "…" : ""}
        </span>
        {!pending && <span style={{ fontSize: 9, color: "rgba(255,255,255,0.3)" }}>{open ? "▲" : "▼"}</span>}
      </button>
      {open && !pending && <pre style={S.toolJson}>{JSON.stringify(tc.result, null, 2)}</pre>}
    </div>
  );
}

function renderMarkdown(text: string, streaming?: boolean) {
  const lines = text.split("\n");
  const nodes = lines.map((line, i) => {
    if (line.startsWith("### ")) {
      return <p key={i} style={{ fontWeight: 700, fontSize: 12, margin: "8px 0 3px", color: "rgba(255,255,255,0.92)" }}>{line.slice(4)}</p>;
    }
    if (line.startsWith("## ")) {
      return <p key={i} style={{ fontWeight: 700, fontSize: 13, margin: "10px 0 3px", color: "rgba(255,255,255,0.92)" }}>{line.slice(3)}</p>;
    }
    if (line.trim() === "") {
      return <div key={i} style={{ height: 5 }} />;
    }
    const parts = line.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
      part.startsWith("**") && part.endsWith("**")
        ? <strong key={j}>{part.slice(2, -2)}</strong>
        : part
    );
    return <p key={i} style={S.bubbleText}>{parts}</p>;
  });
  if (streaming) {
    const last = nodes[nodes.length - 1] as any;
    nodes[nodes.length - 1] = <span key="cursor" style={S.cursor}>▌</span>;
    nodes.splice(nodes.length - 1, 0, last);
  }
  return nodes;
}

function Bubble({ msg }: { msg: DisplayMessage }) {
  const isUser = msg.role === "user";
  return (
    <div style={{ ...S.bubble, ...(isUser ? S.bubbleUser : S.bubbleAI) }}>
      {!isUser && msg.tool_calls && msg.tool_calls.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 8 }}>
          {msg.tool_calls.map((tc, i) => (
            <ToolBadge key={i} tc={tc} pending={!tc.result || Object.keys(tc.result).length === 0} />
          ))}
        </div>
      )}
      {isUser
        ? msg.content
          ? <p style={S.bubbleText}>{msg.content}</p>
          : null
        : msg.content
          ? <>{renderMarkdown(msg.content, msg.streaming)}</>
          : msg.streaming
            ? <p style={{ ...S.bubbleText, color: "rgba(255,255,255,0.35)" }}><span style={S.cursor}>▌</span></p>
            : null}
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export default function WidgetChat() {
  const [token,    setToken]    = useState<string | null>(null);
  const [open,     setOpen]     = useState(false);
  const [input,    setInput]    = useState("");
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [history,  setHistory]  = useState<HistoryMessage[]>([]);
  const [busy,     setBusy]     = useState(false);
  const [error,    setError]    = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Read token from URL on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setToken(params.get("token"));
  }, []);

  // Notify parent page to resize iframe whenever open state changes
  useEffect(() => {
    const size = open ? EXPANDED : COLLAPSED;
    window.parent.postMessage({ type: "soukpilot:resize", ...size }, "*");
  }, [open]);

  // Allow the snippet's drag overlay to toggle open state via postMessage
  useEffect(() => {
    function onMessage(e: MessageEvent) {
      if (e.data?.type === "soukpilot:toggle") setOpen(o => !o);
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Send message ────────────────────────────────────────────────────────────

  async function send(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || busy || !token) return;
    setInput(""); setError(null); setBusy(true);

    const toolsAccum: ToolCall[] = [];
    let responseText = "";

    setMessages(prev => [
      ...prev,
      { role: "user",      content: msg },
      { role: "assistant", content: "", tool_calls: [], streaming: true },
    ]);

    const updateLast = () => setMessages(prev => {
      const copy = [...prev];
      copy[copy.length - 1] = { role: "assistant", content: responseText, tool_calls: toolsAccum.map(t => ({ ...t })), streaming: true };
      return copy;
    });

    try {
      const res = await fetch(`${BASE}/api/widget/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, message: msg, history }),
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
          let ev: Record<string, unknown>;
          try { ev = JSON.parse(part.slice(6)); } catch { continue; }

          if (ev.type === "tool_start") {
            toolsAccum.push({ tool: ev.tool as string, args: (ev.args as Record<string, unknown>) ?? {}, result: {} });
            updateLast();
          } else if (ev.type === "tool_result") {
            const idx = toolsAccum.findLastIndex(tc => tc.tool === ev.tool);
            if (idx >= 0) toolsAccum[idx] = { ...toolsAccum[idx], result: (ev.result as Record<string, unknown>) ?? {} };
            updateLast();
          } else if (ev.type === "text") {
            responseText += ev.text as string;
            updateLast();
          } else if (ev.type === "done") {
            setHistory(h => [...h, { role: "user", content: msg }, { role: "assistant", content: responseText }]);
            setMessages(prev => {
              const copy = [...prev];
              copy[copy.length - 1] = { role: "assistant", content: responseText, tool_calls: toolsAccum.map(t => ({ ...t })), streaming: false };
              return copy;
            });
          } else if (ev.type === "error") {
            throw new Error(ev.error as string);
          }
        }
      }
    } catch (e: any) {
      setError(e?.message ?? "Something went wrong.");
      setMessages(prev => prev.slice(0, -2));
    } finally {
      setBusy(false);
    }
  }

  // ── Collapsed: floating toggle button ────────────────────────────────────────

  if (!open) {
    return (
      <div style={S.collapsedRoot}>
        <button
          style={S.fab}
          onClick={() => setOpen(true)}
          title="Open SoukPilot AI"
        >
          <LogoIcon size={34} iconOnly={true} white={true} />
        </button>
      </div>
    );
  }

  // ── Expanded: full chat panel ─────────────────────────────────────────────────

  return (
    <div style={S.shell}>

      {/* Header */}
      <div style={S.header}>
        <div style={S.headerLogo}>
          <LogoIcon size={22} white={true} />
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={S.liveChip}>
            <span style={S.liveDot} />
            <span style={{ fontSize: 10, fontWeight: 600, color: "#34d399", letterSpacing: "0.5px" }}>LIVE</span>
          </div>
          <button style={S.closeBtn} onClick={() => setOpen(false)} title="Collapse">
            ✕
          </button>
        </div>
      </div>

      {/* Messages */}
      <div style={S.chatArea}>
        {messages.length === 0 && !busy && (
          <div style={S.emptyState}>
            <p style={S.emptyTitle}>Ask me anything about your business</p>
            <div style={S.examples}>
              {EXAMPLES.map(p => (
                <button key={p} style={S.exampleBtn} onClick={() => send(p)}>{p}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => <Bubble key={i} msg={m} />)}
        <div ref={bottomRef} />
      </div>

      {error && <div style={S.errorBanner}>⚠ {error}</div>}

      {/* Input */}
      <div style={S.inputRow}>
        <input
          style={S.input}
          type="text"
          placeholder="Ask about stock, sales, orders…"
          value={input}
          disabled={busy}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && send()}
        />
        <button
          style={{ ...S.sendBtn, opacity: input.trim() && !busy ? 1 : 0.45 }}
          disabled={!input.trim() || busy}
          onClick={() => send()}
        >
          {busy ? "…" : "→"}
        </button>
      </div>

      <div style={S.poweredBy}>
        Powered by <span style={{ color: "#818cf8", fontWeight: 600 }}>SoukPilot AI</span>
      </div>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const S: Record<string, React.CSSProperties> = {
  // Collapsed root: transparent so only the button is visible
  collapsedRoot: {
    width: "100vw", height: "100vh",
    background: "transparent",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontFamily: "'Inter', system-ui, sans-serif",
  },
  // Floating action button
  fab: {
    width: 56, height: 56, borderRadius: "50%",
    background: "linear-gradient(135deg, #818cf8, #6366f1)",
    border: "none", cursor: "pointer",
    display: "flex", alignItems: "center", justifyContent: "center",
    boxShadow: "0 4px 20px rgba(99,102,241,0.5)",
    transition: "transform 0.15s ease, box-shadow 0.15s ease",
  },
  // Full panel shell
  shell: {
    display: "flex", flexDirection: "column",
    height: "100vh",
    background: "#060818",
    fontFamily: "'Inter', system-ui, sans-serif",
    color: "rgba(255,255,255,0.92)",
    fontSize: 13, overflow: "hidden",
  },
  header: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    padding: "12px 16px",
    borderBottom: "1px solid rgba(255,255,255,0.07)",
    background: "rgba(255,255,255,0.03)",
    flexShrink: 0,
  },
  headerLogo: { display: "flex", alignItems: "center", gap: 8 },
  headerTitle: { fontWeight: 700, fontSize: 13, letterSpacing: "0.3px" },
  liveChip: {
    display: "flex", alignItems: "center", gap: 5,
    background: "rgba(52,211,153,0.07)", border: "1px solid rgba(52,211,153,0.2)",
    borderRadius: 100, padding: "3px 8px",
  },
  liveDot: {
    width: 5, height: 5, borderRadius: "50%", background: "#34d399",
    display: "inline-block", animation: "live-pulse 2.5s ease-in-out infinite",
  },
  closeBtn: {
    background: "none", border: "none", color: "rgba(255,255,255,0.35)",
    fontSize: 15, cursor: "pointer", padding: "2px 6px", borderRadius: 4, lineHeight: 1,
  },
  chatArea: {
    flex: 1, overflowY: "auto", padding: "12px 14px",
    display: "flex", flexDirection: "column", gap: 10,
  },
  emptyState: { textAlign: "center", padding: "24px 8px" },
  emptyTitle: { color: "rgba(255,255,255,0.5)", fontSize: 12, marginBottom: 14 },
  examples: { display: "flex", flexDirection: "column", gap: 6, alignItems: "center" },
  exampleBtn: {
    background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 100, padding: "6px 14px", color: "rgba(255,255,255,0.45)",
    fontSize: 11.5, cursor: "pointer", whiteSpace: "nowrap",
  },
  bubble: { maxWidth: "88%", borderRadius: 10, padding: "10px 13px" },
  bubbleUser: { alignSelf: "flex-end", background: "#818cf8", color: "#fff" },
  bubbleAI: { alignSelf: "flex-start", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" },
  bubbleText: { fontSize: 13, lineHeight: 1.6, margin: 0, whiteSpace: "pre-wrap" },
  cursor: { display: "inline-block", animation: "blink 1s step-end infinite", marginLeft: 1 },
  toolBadge: { background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 6, overflow: "hidden" },
  toolHeader: {
    display: "flex", alignItems: "center", gap: 6, width: "100%", padding: "5px 9px",
    background: "none", border: "none", cursor: "pointer", color: "rgba(255,255,255,0.4)", fontSize: 11, textAlign: "left",
  },
  toolJson: { padding: "8px 10px", borderTop: "1px solid rgba(255,255,255,0.06)", fontSize: 10.5, overflowX: "auto", margin: 0, color: "rgba(255,255,255,0.35)" },
  errorBanner: {
    background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)",
    borderRadius: 8, padding: "8px 12px", margin: "0 14px 8px", color: "#f87171", fontSize: 12,
  },
  inputRow: {
    display: "flex", gap: 8, padding: "10px 14px",
    borderTop: "1px solid rgba(255,255,255,0.07)", flexShrink: 0,
  },
  input: {
    flex: 1, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: 8, padding: "9px 12px", color: "rgba(255,255,255,0.92)",
    fontSize: 13, fontFamily: "inherit", outline: "none",
  },
  sendBtn: {
    background: "#818cf8", color: "#fff", border: "none", borderRadius: 8,
    padding: "9px 16px", fontWeight: 700, fontSize: 15, cursor: "pointer",
  },
  poweredBy: {
    textAlign: "center", fontSize: 10, color: "rgba(255,255,255,0.2)",
    padding: "5px 0 8px", flexShrink: 0,
  },
};
