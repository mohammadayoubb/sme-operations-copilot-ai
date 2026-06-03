import { useRef, useState } from "react";
import PageShell from "../components/PageShell";
import { voiceApi } from "../services/api";

interface CommandResult {
  transcript: string;
  intent: string;
  params: Record<string, unknown>;
}

const INTENT_COLORS: Record<string, string> = {
  record_sale:  "#22c55e",
  check_stock:  "#6c63ff",
  create_order: "#f59e0b",
  get_summary:  "#3b82f6",
  other:        "var(--text-muted)",
};

export default function VoiceAssistant() {
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CommandResult | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  async function processBlob(blob: Blob) {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const file = new File([blob], "audio.webm", { type: blob.type || "audio/webm" });
      const { data: t } = await voiceApi.transcribe(file);
      const { data: c } = await voiceApi.command(t.transcript);
      setResult(c);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Processing failed.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleRecording() {
    if (recording) {
      // Stop
      mediaRef.current?.stop();
      setRecording(false);
      return;
    }

    setError(null);
    setResult(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];

      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        processBlob(blob);
      };

      mr.start();
      mediaRef.current = mr;
      setRecording(true);
    } catch {
      setError("Microphone access denied. Please allow microphone in your browser.");
    }
  }

  async function handleFile(file: File) {
    await processBlob(file);
  }

  const intentColor = result ? (INTENT_COLORS[result.intent] ?? INTENT_COLORS.other) : "var(--text)";

  return (
    <PageShell title="Voice Assistant" subtitle="Speak a sale, order, or command — Whisper transcribes it and the AI parses the intent">
      <div style={styles.card}>
        <div style={styles.micWrapper}>
          <button
            style={{ ...styles.micBtn, ...(recording ? styles.micBtnActive : {}), opacity: busy ? 0.5 : 1 }}
            disabled={busy}
            onClick={toggleRecording}
            title={recording ? "Click to stop recording" : "Click to start recording"}
          >
            <span style={styles.micIcon}>{recording ? "⏹" : "🎙"}</span>
          </button>
          <p style={styles.micStatus}>
            {busy ? "Processing audio…" : recording ? "Recording… click to stop" : "Click to start recording"}
          </p>
        </div>

        <div style={styles.divider}>or upload an audio file</div>

        <div style={{ textAlign: "center" }}>
          <input
            ref={fileRef}
            type="file"
            accept="audio/*"
            style={{ display: "none" }}
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
          <button style={{ ...styles.uploadBtn, opacity: busy ? 0.5 : 1 }} disabled={busy} onClick={() => fileRef.current?.click()}>
            Choose audio file
          </button>
          <p style={styles.hint}>Supports: MP3, WAV, M4A, WebM, OGG · Max 25 MB</p>
        </div>
      </div>

      {error && <div style={styles.errorBanner}>⚠ {error}</div>}

      {result ? (
        <div style={styles.section}>
          <div style={styles.resultCard}>
            <div style={styles.transcriptSection}>
              <span style={styles.transcriptLabel}>Transcript</span>
              <p style={styles.transcriptText}>"{result.transcript}"</p>
            </div>
            <div style={styles.dividerH} />
            <div style={styles.intentSection}>
              <div style={styles.intentRow}>
                <span style={styles.intentLabel}>Detected intent</span>
                <span style={{ ...styles.intentBadge, background: intentColor + "22", color: intentColor }}>
                  {result.intent.replace(/_/g, " ").toUpperCase()}
                </span>
              </div>
              {Object.keys(result.params).length > 0 && (
                <div style={styles.paramsWrap}>
                  <span style={styles.paramsLabel}>Parameters</span>
                  <pre style={styles.paramsJson}>{JSON.stringify(result.params, null, 2)}</pre>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : !busy && (
        <>
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>Example commands you can say</h3>
            <div style={styles.exampleGrid}>
              {[
                { cmd: "Add sale: 3 Pepsi and 2 chips", intent: "record_sale" },
                { cmd: "How many Nutella do I have left?", intent: "check_stock" },
                { cmd: "I need 24 bottles of water from supplier", intent: "create_order" },
                { cmd: "What were my best sellers today?", intent: "get_summary" },
              ].map(({ cmd, intent }) => (
                <div key={cmd} style={styles.exampleCard}>
                  <span style={{ ...styles.exampleIntent, color: INTENT_COLORS[intent] ?? "var(--text-muted)" }}>
                    {intent.replace(/_/g, " ")}
                  </span>
                  <span style={styles.exampleText}>"{cmd}"</span>
                </div>
              ))}
            </div>
          </div>
          <div style={styles.emptyState}>
            Transcript and detected command will appear here after recording or uploading audio.
          </div>
        </>
      )}
    </PageShell>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 32, marginBottom: 28, textAlign: "center" },
  micWrapper: { display: "flex", flexDirection: "column", alignItems: "center", gap: 16, marginBottom: 24 },
  micBtn: {
    width: 80, height: 80, borderRadius: "50%",
    background: "var(--surface2)", border: "2px solid var(--border)",
    display: "flex", alignItems: "center", justifyContent: "center",
    cursor: "pointer", transition: "all 0.2s",
  },
  micBtnActive: { background: "#ef444422", borderColor: "#ef4444", boxShadow: "0 0 0 8px #ef444422" },
  micIcon: { fontSize: 32 },
  micStatus: { color: "var(--text-muted)", fontSize: 13 },
  divider: { color: "var(--text-muted)", margin: "0 0 16px", fontSize: 13 },
  uploadBtn: { background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: 6, padding: "9px 20px", color: "var(--text)", fontSize: 13, cursor: "pointer" },
  hint: { color: "var(--text-muted)", fontSize: 11, marginTop: 8 },
  errorBanner: { background: "#ef444418", border: "1px solid #ef444444", borderRadius: "var(--radius)", padding: "12px 16px", marginBottom: 20, color: "var(--danger)", fontSize: 13 },
  section: { marginBottom: 28 },
  resultCard: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", overflow: "hidden" },
  transcriptSection: { padding: "18px 22px" },
  transcriptLabel: { display: "block", color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 8 },
  transcriptText: { fontSize: 15, fontStyle: "italic", lineHeight: 1.5 },
  dividerH: { height: 1, background: "var(--border)" },
  intentSection: { padding: "16px 22px" },
  intentRow: { display: "flex", alignItems: "center", gap: 14, marginBottom: 12 },
  intentLabel: { color: "var(--text-muted)", fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" },
  intentBadge: { fontSize: 12, fontWeight: 700, padding: "4px 12px", borderRadius: 100 },
  paramsWrap: { marginTop: 4 },
  paramsLabel: { display: "block", color: "var(--text-muted)", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 6 },
  paramsJson: { background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: 6, padding: "10px 14px", fontSize: 12.5, margin: 0 },
  sectionTitle: { fontWeight: 600, marginBottom: 14, fontSize: 15 },
  exampleGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 },
  exampleCard: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "14px 16px", display: "flex", flexDirection: "column", gap: 6 },
  exampleIntent: { fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px" },
  exampleText: { color: "var(--text-muted)", fontSize: 13, fontStyle: "italic" },
  emptyState: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 24, color: "var(--text-muted)", textAlign: "center" },
};
