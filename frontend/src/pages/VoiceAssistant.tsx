import { useEffect, useRef, useState } from "react";
import PageShell from "../components/PageShell";
import { voiceApi } from "../services/api";

const BASE = (import.meta.env.VITE_API_URL as string) ?? "";

type Phase = "idle" | "recording" | "transcribing" | "thinking" | "speaking";

interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
}

interface ToolCall {
  tool: string;
  args: Record<string, unknown>;
  result: Record<string, unknown>;
}

interface ConvMessage {
  role: "user" | "assistant";
  content: string;
  tool_calls?: ToolCall[];
  streaming?: boolean;
  isVoice?: boolean;
}

const PHASE_LABEL: Record<Phase, string> = {
  idle: "Press the mic to speak",
  recording: "Recording… press again to stop",
  transcribing: "Transcribing audio…",
  thinking: "Thinking…",
  speaking: "Speaking…",
};

const TOOL_ICONS: Record<string, string> = {
  check_stock: "📦",
  get_reorder_alerts: "🔮",
  get_sales_summary: "📈",
  get_latest_report: "📊",
  list_recent_orders: "🛍",
  get_price_history: "💰",
  create_order: "✅",
};

const EXAMPLES = [
  { text: "How much Nutella do I have left?", icon: "📦" },
  { text: "What should I reorder this week?", icon: "🔮" },
  { text: "How were my sales compared to last week?", icon: "📈" },
  { text: "Record an order: 2 black hoodies size L, Hamra, cash on delivery", icon: "✅" },
];

// ── sub-components ──────────────────────────────────────────────────────────

function ToolCallBadge({ tc, pending }: { tc: ToolCall; pending?: boolean }) {
  const [open, setOpen] = useState(false);
  const icon = TOOL_ICONS[tc.tool] ?? "🔧";
  return (
    <div style={S.toolBadge}>
      <button style={S.toolHeader} onClick={() => !pending && setOpen((o) => !o)}>
        <span style={S.toolIcon}>{pending ? "⏳" : icon}</span>
        <span style={{ ...S.toolLabel, color: pending ? "var(--text-muted)" : undefined }}>
          {tc.tool.replace(/_/g, " ")}{pending ? "…" : ""}
        </span>
        {!pending && <span style={S.toolChevron}>{open ? "▲" : "▼"}</span>}
      </button>
      {open && !pending && (
        <pre style={S.toolJson}>{JSON.stringify(tc.result, null, 2)}</pre>
      )}
    </div>
  );
}

function ConvBubble({ msg }: { msg: ConvMessage }) {
  const isUser = msg.role === "user";
  return (
    <div style={{ ...S.bubble, ...(isUser ? S.bubbleUser : S.bubbleAI) }}>
      {isUser && msg.isVoice && <span style={S.voiceTag}>🎙 voice</span>}
      {!isUser && msg.tool_calls && msg.tool_calls.length > 0 && (
        <div style={S.toolCalls}>
          {msg.tool_calls.map((tc, i) => (
            <ToolCallBadge
              key={i}
              tc={tc}
              pending={!tc.result || Object.keys(tc.result).length === 0}
            />
          ))}
        </div>
      )}
      {msg.content ? (
        <p style={S.bubbleText}>
          {msg.content}
          {msg.streaming && <span style={S.cursor}>▌</span>}
        </p>
      ) : msg.streaming ? (
        <p style={{ ...S.bubbleText, color: "var(--text-muted)" }}>
          <span style={S.cursor}>▌</span>
        </p>
      ) : null}
    </div>
  );
}

// ── main component ────────────────────────────────────────────────────────────

export default function VoiceAssistant() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [messages, setMessages] = useState<ConvMessage[]>([]);
  const [history, setHistory] = useState<HistoryMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [muted, setMuted] = useState(false);
  const mutedRef = useRef(false);

  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { mutedRef.current = muted; }, [muted]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── recording ──────────────────────────────────────────────────────────────

  async function toggleRecording() {
    if (phase === "speaking") {
      stopSpeaking();
      return;
    }
    if (phase === "recording") {
      mediaRef.current?.stop();
      return;
    }
    if (phase !== "idle") return;

    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : MediaRecorder.isTypeSupported("audio/ogg")
        ? "audio/ogg"
        : "";
      const mr = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      chunksRef.current = [];

      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      mr.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: mimeType || "audio/webm" });
        processAudio(blob, mimeType || "audio/webm");
      };

      mr.start();
      mediaRef.current = mr;
      setPhase("recording");
    } catch {
      setError("Microphone access denied. Please allow microphone in your browser.");
    }
  }

  // ── transcribe → agent ─────────────────────────────────────────────────────

  async function processAudio(blob: Blob, mimeType: string) {
    setPhase("transcribing");
    try {
      const ext = mimeType.includes("ogg") ? ".ogg" : ".webm";
      const file = new File([blob], `audio${ext}`, { type: mimeType });
      const { data: t } = await voiceApi.transcribe(file);
      const transcript: string = t.transcript;
      if (!transcript) throw new Error("No speech detected.");
      await runAgent(transcript, true);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? "Transcription failed.");
      setPhase("idle");
    }
  }

  // ── agent stream ───────────────────────────────────────────────────────────

  async function runAgent(msg: string, isVoice: boolean) {
    setPhase("thinking");

    const userMsg: ConvMessage = { role: "user", content: msg, isVoice };
    const placeholder: ConvMessage = { role: "assistant", content: "", tool_calls: [], streaming: true };
    setMessages((prev) => [...prev, userMsg, placeholder]);

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
      const res = await fetch(`${BASE}/api/agent/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
            toolsAccum.push({
              tool: event.tool as string,
              args: (event.args as Record<string, unknown>) ?? {},
              result: {},
            });
            updateLast();
          } else if (event.type === "tool_result") {
            const last = toolsAccum.findLastIndex((tc) => tc.tool === (event.tool as string));
            if (last >= 0) {
              toolsAccum[last] = { ...toolsAccum[last], result: (event.result as Record<string, unknown>) ?? {} };
            }
            updateLast();
          } else if (event.type === "text") {
            responseText += event.text as string;
            updateLast();
          } else if (event.type === "done") {
            setHistory((h) => [
              ...h,
              { role: "user", content: msg },
              { role: "assistant", content: responseText },
            ]);
            setMessages((prev) => {
              const copy = [...prev];
              copy[copy.length - 1] = {
                role: "assistant",
                content: responseText,
                tool_calls: toolsAccum.map((t) => ({ ...t })),
                streaming: false,
              };
              return copy;
            });
            if (isVoice && !mutedRef.current && responseText) {
              await speakResponse(responseText);
            } else {
              setPhase("idle");
            }
          } else if (event.type === "error") {
            throw new Error(event.error as string);
          }
        }
      }
    } catch (e: any) {
      setError(e?.message ?? "Something went wrong.");
      setMessages((prev) => prev.slice(0, -2));
      setPhase("idle");
    }
  }

  // ── TTS ────────────────────────────────────────────────────────────────────

  async function speakResponse(text: string) {
    setPhase("speaking");
    // Cap at ~600 chars so TTS stays snappy; trim at last space before limit
    const cap = 600;
    const ttsText = text.length > cap
      ? text.substring(0, text.lastIndexOf(" ", cap)) + "…"
      : text;

    try {
      const { data } = await voiceApi.speak(ttsText);
      const blob = new Blob([data as ArrayBuffer], { type: "audio/mpeg" });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      const finish = () => { URL.revokeObjectURL(url); setPhase("idle"); };
      audio.onended = finish;
      audio.onerror = finish;
      await audio.play();
    } catch {
      // Fallback: browser SpeechSynthesis
      try {
        const utt = new SpeechSynthesisUtterance(ttsText);
        utt.onend = () => setPhase("idle");
        utt.onerror = () => setPhase("idle");
        window.speechSynthesis.speak(utt);
      } catch {
        setPhase("idle");
      }
    }
  }

  function stopSpeaking() {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
    window.speechSynthesis?.cancel();
    setPhase("idle");
  }

  function clear() {
    stopSpeaking();
    setMessages([]);
    setHistory([]);
    setError(null);
    setPhase("idle");
  }

  // ── derived ────────────────────────────────────────────────────────────────

  const micIcon = phase === "recording" ? "⏹" : phase === "speaking" ? "🔊" : "🎙";
  const micClickable = phase === "idle" || phase === "recording" || phase === "speaking";

  const micBtnStyle: React.CSSProperties = {
    ...S.micBtn,
    ...(phase === "recording" ? S.micRecording : {}),
    ...(phase === "speaking" ? S.micSpeaking : {}),
    opacity: micClickable ? 1 : 0.45,
    cursor: micClickable ? "pointer" : "default",
  };

  return (
    <PageShell
      title="Voice Assistant"
      subtitle="Speak to your business — Whisper transcribes, the AI agent answers using live data, and responds out loud"
    >
      <style>{`
        @keyframes pulse-ring {
          0%   { box-shadow: 0 0 0 0 rgba(239,68,68,0.45); }
          70%  { box-shadow: 0 0 0 22px rgba(239,68,68,0); }
          100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); }
        }
        @keyframes speak-ring {
          0%   { box-shadow: 0 0 0 0 rgba(99,102,241,0.45); }
          70%  { box-shadow: 0 0 0 22px rgba(99,102,241,0); }
          100% { box-shadow: 0 0 0 0 rgba(99,102,241,0); }
        }
        @keyframes blink { 0%,100% { opacity:1; } 50% { opacity:0; } }
        @keyframes dot-bounce {
          0%,80%,100% { transform:scale(0); opacity:0.4; }
          40%          { transform:scale(1); opacity:1; }
        }
      `}</style>

      {/* ── mic panel ── */}
      <div style={S.micPanel}>
        <button style={micBtnStyle} onClick={toggleRecording} disabled={!micClickable}>
          <span style={{ fontSize: 40, lineHeight: 1 }}>{micIcon}</span>
        </button>

        <p style={S.phaseLabel}>{PHASE_LABEL[phase]}</p>

        {(phase === "transcribing" || phase === "thinking") && (
          <div style={S.dots}>
            {[0, 180, 360].map((delay) => (
              <span key={delay} style={{ ...S.dot, animationDelay: `${delay}ms` }} />
            ))}
          </div>
        )}

        <div style={S.micFooter}>
          <button
            style={{ ...S.muteBtn, ...(muted ? S.mutedActive : {}) }}
            onClick={() => setMuted((m) => !m)}
            title={muted ? "Unmute AI voice" : "Mute AI voice"}
          >
            {muted ? "🔇 Muted" : "🔊 Voice on"}
          </button>
          {messages.length > 0 && (
            <button style={S.clearBtn} onClick={clear} disabled={phase !== "idle"}>
              Clear
            </button>
          )}
        </div>
      </div>

      {/* ── conversation ── */}
      {messages.length > 0 && (
        <div style={S.chat}>
          {messages.map((m, i) => <ConvBubble key={i} msg={m} />)}
          <div ref={bottomRef} />
        </div>
      )}

      {error && <div style={S.errorBanner}>⚠ {error}</div>}

      {/* ── empty state ── */}
      {messages.length === 0 && phase === "idle" && (
        <div style={S.examplesWrap}>
          <p style={S.examplesTitle}>Try saying…</p>
          <div style={S.examplesGrid}>
            {EXAMPLES.map(({ text, icon }) => (
              <div key={text} style={S.exampleCard}>
                <span style={S.exIcon}>{icon}</span>
                <span style={S.exText}>"{text}"</span>
              </div>
            ))}
          </div>
          <p style={S.poweredBy}>Powered by OpenAI Whisper STT · GPT-4o Agent · TTS Nova</p>
        </div>
      )}
    </PageShell>
  );
}

// ── styles ────────────────────────────────────────────────────────────────────

const S: Record<string, React.CSSProperties> = {
  // mic panel
  micPanel: {
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    padding: "36px 24px 24px",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 14,
    marginBottom: 24,
  },
  micBtn: {
    width: 96,
    height: 96,
    borderRadius: "50%",
    background: "var(--surface2)",
    border: "2px solid var(--border)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "all 0.2s",
  },
  micRecording: {
    background: "#ef444418",
    borderColor: "#ef4444",
    animation: "pulse-ring 1.4s ease-out infinite",
  },
  micSpeaking: {
    background: "#6366f118",
    borderColor: "#6366f1",
    animation: "speak-ring 1.4s ease-out infinite",
  },
  phaseLabel: {
    color: "var(--text-muted)",
    fontSize: 13,
    margin: 0,
  },
  dots: {
    display: "flex",
    gap: 6,
  },
  dot: {
    display: "inline-block",
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: "var(--text-muted)",
    animation: "dot-bounce 1.2s infinite ease-in-out both",
  },
  micFooter: {
    display: "flex",
    gap: 10,
    marginTop: 4,
  },
  muteBtn: {
    background: "var(--surface2)",
    border: "1px solid var(--border)",
    borderRadius: 6,
    padding: "7px 14px",
    color: "var(--text-muted)",
    fontSize: 12,
    cursor: "pointer",
  },
  mutedActive: {
    background: "#ef444418",
    borderColor: "#ef444466",
    color: "#ef4444",
  },
  clearBtn: {
    background: "var(--surface2)",
    border: "1px solid var(--border)",
    borderRadius: 6,
    padding: "7px 14px",
    color: "var(--text-muted)",
    fontSize: 12,
    cursor: "pointer",
  },

  // conversation
  chat: {
    display: "flex",
    flexDirection: "column",
    gap: 14,
    marginBottom: 20,
    maxHeight: 480,
    overflowY: "auto",
    paddingRight: 4,
  },
  bubble: {
    maxWidth: "84%",
    borderRadius: "var(--radius)",
    padding: "12px 16px",
  },
  bubbleUser: {
    alignSelf: "flex-end",
    background: "var(--accent)",
    color: "#fff",
  },
  bubbleAI: {
    alignSelf: "flex-start",
    background: "var(--surface)",
    border: "1px solid var(--border)",
  },
  voiceTag: {
    display: "block",
    fontSize: 10,
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: "0.5px",
    opacity: 0.7,
    marginBottom: 5,
  },
  bubbleText: {
    fontSize: 14,
    lineHeight: 1.6,
    margin: 0,
    whiteSpace: "pre-wrap",
  },
  cursor: {
    display: "inline-block",
    animation: "blink 1s step-end infinite",
    marginLeft: 1,
  },

  // tool calls
  toolCalls: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
    marginBottom: 10,
  },
  toolBadge: {
    background: "var(--surface2)",
    border: "1px solid var(--border)",
    borderRadius: 6,
    overflow: "hidden",
  },
  toolHeader: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    width: "100%",
    padding: "7px 12px",
    background: "none",
    border: "none",
    cursor: "pointer",
    color: "var(--text-muted)",
    fontSize: 12,
    textAlign: "left" as const,
  },
  toolIcon: { fontSize: 14 },
  toolLabel: { flex: 1, fontWeight: 600 },
  toolChevron: { fontSize: 10 },
  toolJson: {
    padding: "10px 14px",
    borderTop: "1px solid var(--border)",
    fontSize: 11.5,
    overflowX: "auto",
    margin: 0,
    color: "var(--text-muted)",
  },

  // error
  errorBanner: {
    background: "#ef444418",
    border: "1px solid #ef444444",
    borderRadius: "var(--radius)",
    padding: "12px 16px",
    marginBottom: 16,
    color: "var(--danger)",
    fontSize: 13,
  },

  // empty state
  examplesWrap: {
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    padding: "28px 24px",
  },
  examplesTitle: {
    fontWeight: 600,
    fontSize: 14,
    marginBottom: 14,
    marginTop: 0,
  },
  examplesGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 10,
    marginBottom: 20,
  },
  exampleCard: {
    background: "var(--surface2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    padding: "12px 14px",
    display: "flex",
    alignItems: "flex-start",
    gap: 10,
  },
  exIcon: { fontSize: 18, flexShrink: 0 },
  exText: {
    color: "var(--text-muted)",
    fontSize: 13,
    fontStyle: "italic",
    lineHeight: 1.4,
  },
  poweredBy: {
    color: "var(--text-muted)",
    fontSize: 11,
    textAlign: "center" as const,
    margin: 0,
  },
};
