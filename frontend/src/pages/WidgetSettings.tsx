import { useEffect, useState } from "react";
import PageShell from "../components/PageShell";

const BASE = (import.meta.env.VITE_API_URL as string) ?? "";
const FRONTEND_ORIGIN = window.location.origin;

interface WidgetToken {
  token: string;
  label: string;
  business_id: number;
  created_at: string;
}

function snippet(token: string) {
  return `<script>
(function () {
  /* Wrapper holds position; iframe fills it; handle sits on top for drag */
  var wrapper = document.createElement('div');
  wrapper.style.cssText = [
    'position:fixed', 'bottom:24px', 'right:24px',
    'width:64px', 'height:64px', 'border-radius:50%',
    'z-index:9999',
    'transition:width 0.22s ease,height 0.22s ease,border-radius 0.22s ease',
    'box-shadow:0 4px 20px rgba(99,102,241,0.5)',
  ].join(';');

  var iframe = document.createElement('iframe');
  iframe.src = '${FRONTEND_ORIGIN}/widget?token=${token}';
  iframe.allow = 'microphone';
  iframe.setAttribute('scrolling', 'no');
  iframe.style.cssText = 'width:100%;height:100%;border:none;border-radius:inherit;display:block;background:transparent;';

  /* Transparent overlay — captures mouse events so the iframe never swallows them */
  var handle = document.createElement('div');
  handle.style.cssText = 'position:absolute;inset:0;z-index:1;cursor:grab;border-radius:inherit;';

  wrapper.appendChild(iframe);
  wrapper.appendChild(handle);
  document.body.appendChild(wrapper);

  /* ── Drag ── */
  var dragging = false, startX, startY, origRight, origBottom;

  var pressed = false, wasDrag = false;

  handle.addEventListener('mousedown', function (e) {
    pressed = true;
    wasDrag = false;
    startX = e.clientX;
    startY = e.clientY;
    var rect = wrapper.getBoundingClientRect();
    origRight  = window.innerWidth  - rect.right;
    origBottom = window.innerHeight - rect.bottom;
    wrapper.style.transition = 'none';
    e.preventDefault();
  });

  document.addEventListener('mousemove', function (e) {
    if (!pressed) return;
    var dx = e.clientX - startX, dy = e.clientY - startY;
    if (!wasDrag && Math.sqrt(dx * dx + dy * dy) < 5) return;
    wasDrag = true;
    handle.style.cursor = 'grabbing';
    var newRight  = Math.max(8, Math.min(origRight  - dx, window.innerWidth  - 72));
    var newBottom = Math.max(8, Math.min(origBottom - dy, window.innerHeight - 72));
    wrapper.style.right  = newRight  + 'px';
    wrapper.style.bottom = newBottom + 'px';
    wrapper.style.left = 'auto';
    wrapper.style.top  = 'auto';
  });

  document.addEventListener('mouseup', function () {
    if (!pressed) return;
    pressed = false;
    if (wasDrag) {
      handle.style.cursor = 'grab';
      wrapper.style.transition = 'width 0.22s ease,height 0.22s ease,border-radius 0.22s ease';
    } else {
      /* It was a tap/click — tell the widget to toggle */
      iframe.contentWindow.postMessage({ type: 'soukpilot:toggle' }, '*');
    }
    wasDrag = false;
  });

  /* ── Resize on open/close ── */
  window.addEventListener('message', function (e) {
    if (!e.data || e.data.type !== 'soukpilot:resize') return;
    var w = e.data.w, h = e.data.h;
    var expanded = w > 100;
    var pad = 8;

    var safeW = Math.min(w, window.innerWidth  - pad * 2);
    var safeH = Math.min(h, window.innerHeight - pad * 2);

    wrapper.style.width        = safeW + 'px';
    wrapper.style.height       = safeH + 'px';
    wrapper.style.borderRadius = expanded ? '16px' : '50%';
    wrapper.style.boxShadow    = expanded ? '0 12px 48px rgba(0,0,0,0.4)' : '0 4px 20px rgba(99,102,241,0.5)';

    if (expanded) {
      /* Nudge so the full panel is visible — clamp bottom and right */
      var b = Math.max(pad, Math.min(parseFloat(wrapper.style.bottom) || 24, window.innerHeight - safeH - pad));
      var r = Math.max(pad, Math.min(parseFloat(wrapper.style.right)  || 24, window.innerWidth  - safeW - pad));
      wrapper.style.bottom = b + 'px';
      wrapper.style.right  = r + 'px';
    }

    /* Hide handle when open so the widget is fully interactive */
    handle.style.display = expanded ? 'none' : 'block';
  });
})();
<\/script>`;
}

export default function WidgetSettings() {
  const [tokens, setTokens] = useState<WidgetToken[]>([]);
  const [label, setLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedToken, setCopiedToken] = useState<string | null>(null);
  const [openSnippet, setOpenSnippet] = useState<string | null>(null);

  function authHeaders(): Record<string, string> {
    const token = localStorage.getItem("soukpilot_token");
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async function load() {
    try {
      const res = await fetch(`${BASE}/api/widget/tokens`, { headers: authHeaders() });
      if (res.ok) setTokens(await res.json());
    } catch { /* non-fatal */ }
  }

  useEffect(() => { load(); }, []);

  async function create() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${BASE}/api/widget/tokens`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ label: label.trim() || "My Widget" }),
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Failed");
      setLabel("");
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function revoke(token: string) {
    try {
      await fetch(`${BASE}/api/widget/tokens/${token}`, { method: "DELETE", headers: authHeaders() });
      await load();
      if (openSnippet === token) setOpenSnippet(null);
    } catch { /* non-fatal */ }
  }

  async function copy(text: string, token: string) {
    await navigator.clipboard.writeText(text);
    setCopiedToken(token);
    setTimeout(() => setCopiedToken(null), 2000);
  }

  return (
    <PageShell title="Widget Embed" subtitle="Generate a snippet to embed the SoukPilot AI assistant on any website">

      {/* How it works */}
      <div style={S.infoCard}>
        <div style={S.infoGrid}>
          {[
            { step: "1", text: "Create a token for your site" },
            { step: "2", text: "Paste the snippet into your website's HTML" },
            { step: "3", text: "The AI assistant appears as a floating widget" },
          ].map(({ step, text }) => (
            <div key={step} style={S.infoStep}>
              <span style={S.stepNum}>{step}</span>
              <span style={S.stepText}>{text}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Create token */}
      <div style={S.card}>
        <h3 style={S.cardTitle}>Create Embed Token</h3>
        <div style={S.row}>
          <input
            style={S.input}
            type="text"
            placeholder="Token label  (e.g. My Shop Website)"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && create()}
          />
          <button style={S.btn} onClick={create} disabled={busy}>
            {busy ? "Creating…" : "Generate Token"}
          </button>
        </div>
        {error && <p style={S.error}>⚠ {error}</p>}
      </div>

      {/* Token list */}
      <div style={S.section}>
        <h3 style={S.sectionTitle}>Active Tokens</h3>
        {tokens.length === 0 ? (
          <div style={S.empty}>No tokens yet — create one above to get your embed snippet.</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {tokens.map((t) => (
              <div key={t.token} style={S.tokenCard}>
                <div style={S.tokenHeader}>
                  <div>
                    <div style={S.tokenLabel}>{t.label}</div>
                    <div style={S.tokenMeta}>
                      <code style={S.tokenCode}>{t.token}</code>
                      <span style={S.tokenDate}>· {new Date(t.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <div style={S.tokenActions}>
                    <button
                      style={S.actionBtn}
                      onClick={() => setOpenSnippet(openSnippet === t.token ? null : t.token)}
                    >
                      {openSnippet === t.token ? "Hide Snippet" : "Get Snippet"}
                    </button>
                    <button
                      style={{ ...S.actionBtn, color: "var(--danger)", borderColor: "rgba(248,113,113,0.25)" }}
                      onClick={() => revoke(t.token)}
                    >
                      Revoke
                    </button>
                  </div>
                </div>

                {openSnippet === t.token && (
                  <div style={S.snippetBox}>
                    <div style={S.snippetHeader}>
                      <span style={S.snippetLabel}>Embed snippet</span>
                      <button
                        style={{ ...S.actionBtn, fontSize: 12 }}
                        onClick={() => copy(snippet(t.token), t.token)}
                      >
                        {copiedToken === t.token ? "✓ Copied!" : "Copy"}
                      </button>
                    </div>
                    <pre style={S.snippetPre}>{snippet(t.token)}</pre>
                    <div style={S.snippetTip}>
                      Paste this before <code style={S.inlineCode}>&lt;/body&gt;</code> on any page.
                      The assistant will appear as a floating panel in the bottom-right corner.
                    </div>
                    <div style={S.previewRow}>
                      <a
                        href={`/widget?token=${t.token}`}
                        target="_blank"
                        rel="noreferrer"
                        style={S.previewLink}
                      >
                        Open widget preview ↗
                      </a>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

    </PageShell>
  );
}

const S: Record<string, React.CSSProperties> = {
  infoCard: {
    background: "rgba(129,140,248,0.06)",
    border: "1px solid rgba(129,140,248,0.15)",
    borderRadius: "var(--radius)",
    padding: "20px 24px",
    marginBottom: 24,
  },
  infoGrid: { display: "flex", gap: 32, flexWrap: "wrap" },
  infoStep: { display: "flex", alignItems: "center", gap: 10 },
  stepNum: {
    width: 24, height: 24, borderRadius: "50%",
    background: "rgba(129,140,248,0.2)", border: "1px solid rgba(129,140,248,0.35)",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 11, fontWeight: 700, color: "#a5b4fc", flexShrink: 0,
  } as React.CSSProperties,
  stepText: { fontSize: 13, color: "rgba(255,255,255,0.7)" },
  card: {
    background: "var(--surface)", border: "1px solid var(--border)",
    borderRadius: "var(--radius)", padding: "20px 24px", marginBottom: 28,
  },
  cardTitle: { fontWeight: 600, fontSize: 14, marginBottom: 14 },
  row: { display: "flex", gap: 10, alignItems: "center" },
  input: {
    flex: 1, background: "var(--surface2)", border: "1px solid var(--border)",
    borderRadius: 6, padding: "10px 14px", color: "var(--text)", fontSize: 14,
  },
  btn: {
    background: "var(--accent)", color: "#fff", border: "none",
    borderRadius: 6, padding: "10px 22px", fontWeight: 600, fontSize: 14,
    whiteSpace: "nowrap",
  } as React.CSSProperties,
  error: { color: "var(--danger)", fontSize: 12, marginTop: 8 },
  section: { marginBottom: 28 },
  sectionTitle: { fontWeight: 600, fontSize: 15, marginBottom: 12 },
  empty: {
    background: "var(--surface)", border: "1px solid var(--border)",
    borderRadius: "var(--radius)", padding: "24px", color: "var(--text-muted)",
    textAlign: "center", fontSize: 13,
  } as React.CSSProperties,
  tokenCard: {
    background: "var(--surface)", border: "1px solid var(--border)",
    borderRadius: "var(--radius)", overflow: "hidden",
  },
  tokenHeader: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    padding: "16px 20px", flexWrap: "wrap", gap: 12,
  } as React.CSSProperties,
  tokenLabel: { fontWeight: 600, fontSize: 14, marginBottom: 4 },
  tokenMeta: { display: "flex", alignItems: "center", gap: 8 },
  tokenCode: {
    background: "var(--surface2)", border: "1px solid var(--border)",
    borderRadius: 4, padding: "2px 7px", fontSize: 11.5, fontFamily: "monospace",
    color: "var(--text-muted)",
  },
  tokenDate: { color: "var(--text-muted)", fontSize: 12 },
  tokenActions: { display: "flex", gap: 8 },
  actionBtn: {
    background: "var(--surface2)", border: "1px solid var(--border)",
    borderRadius: 6, padding: "7px 14px", color: "var(--text-muted)",
    fontSize: 12, fontWeight: 500, cursor: "pointer",
  },
  snippetBox: {
    borderTop: "1px solid var(--border)",
    padding: "16px 20px",
    background: "var(--surface2)",
  },
  snippetHeader: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 },
  snippetLabel: { fontSize: 12, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" },
  snippetPre: {
    background: "#0c0e1a", border: "1px solid var(--border)", borderRadius: 8,
    padding: "14px 16px", fontSize: 11.5, overflowX: "auto", color: "rgba(255,255,255,0.75)",
    lineHeight: 1.6, whiteSpace: "pre", margin: 0,
  },
  snippetTip: { marginTop: 10, fontSize: 12, color: "var(--text-muted)", lineHeight: 1.6 },
  inlineCode: {
    background: "var(--surface)", border: "1px solid var(--border)",
    borderRadius: 3, padding: "1px 5px", fontSize: 11, fontFamily: "monospace",
  },
  previewRow: { marginTop: 10 },
  previewLink: {
    color: "var(--accent)", fontSize: 12, textDecoration: "underline", cursor: "pointer",
  },
};
